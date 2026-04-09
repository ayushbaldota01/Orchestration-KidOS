"""
AI Chatbot Backend – FastAPI
Connects to local Ollama (text) and ComfyUI (image) services.
"""

import json
import re
import time
import uuid
import base64
import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Config ──────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5"

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_PROMPT_EP = f"{COMFYUI_URL}/prompt"
COMFYUI_HISTORY_EP = f"{COMFYUI_URL}/history"
COMFYUI_VIEW_EP = f"{COMFYUI_URL}/view"

WORKFLOW_PATH = Path(__file__).parent / "workflows" / "comfy_workflow.json"

IMAGE_KEYWORDS = [
    "draw", "generate image", "create image", "picture",
    "art", "illustration", "paint", "sketch", "make an image",
    "generate a picture", "create a picture", "render",
    "design", "visualize", "depict", "imagine an image",
    "show me", "create art",
]

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Chatbot")

# Mount static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


# ── Helpers ─────────────────────────────────────────────────────────────────

def is_image_request(message: str) -> bool:
    """Check whether the user message implies image generation."""
    lower = message.lower()
    return any(kw in lower for kw in IMAGE_KEYWORDS)


def extract_image_prompt(message: str) -> str:
    """Pull out a cleaner prompt for Stable Diffusion."""
    lower = message.lower()
    prompt = message
    # Strip common command prefixes so the SD prompt is cleaner
    for kw in IMAGE_KEYWORDS:
        if kw in lower:
            idx = lower.find(kw)
            prompt = message[idx + len(kw):].strip(" :.,!?-–—of")
            if prompt:
                break
    return prompt if prompt else message


async def query_ollama(prompt: str) -> str:
    """Send a prompt to Ollama and return the full generated text."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


async def query_comfyui(prompt_text: str) -> str:
    """Queue an image generation job in ComfyUI and return the image as base64."""
    # Load & patch workflow
    workflow = json.loads(WORKFLOW_PATH.read_text())
    workflow["3"]["inputs"]["seed"] = int(time.time()) % (2**32)
    workflow["6"]["inputs"]["text"] = prompt_text

    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Queue the prompt
        resp = await client.post(COMFYUI_PROMPT_EP, json=payload)
        resp.raise_for_status()
        result = resp.json()
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")

        # Poll history until the job finishes
        for _ in range(300):  # up to ~5 min
            await asyncio.sleep(1)
            hist_resp = await client.get(f"{COMFYUI_HISTORY_EP}/{prompt_id}")
            if hist_resp.status_code != 200:
                continue
            history = hist_resp.json()
            if prompt_id in history:
                break
        else:
            raise RuntimeError("ComfyUI generation timed out")

        # Extract image info from the history
        outputs = history[prompt_id].get("outputs", {})
        for node_id, node_out in outputs.items():
            images = node_out.get("images", [])
            if images:
                img_info = images[0]
                filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")
                img_type = img_info.get("type", "output")

                params = {"filename": filename, "type": img_type}
                if subfolder:
                    params["subfolder"] = subfolder

                img_resp = await client.get(COMFYUI_VIEW_EP, params=params)
                img_resp.raise_for_status()
                b64 = base64.b64encode(img_resp.content).decode("utf-8")
                return f"data:image/png;base64,{b64}"

        raise RuntimeError("No image found in ComfyUI output")


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the frontend."""
    from fastapi.responses import HTMLResponse
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "").strip()
    if not user_message:
        return JSONResponse({"type": "error", "content": "Empty message"}, status_code=400)

    try:
        if is_image_request(user_message):
            prompt = extract_image_prompt(user_message)
            # Optionally enhance prompt via Ollama
            enhanced = await query_ollama(
                f"You are an expert Stable Diffusion prompt writer. "
                f"Convert the following request into a concise, descriptive image generation prompt "
                f"with artistic details. Only output the prompt, nothing else.\n\n"
                f"Request: {prompt}"
            )
            image_prompt = enhanced if enhanced else prompt
            image_b64 = await query_comfyui(image_prompt)
            return JSONResponse({
                "type": "image",
                "content": image_b64,
                "caption": f"🎨 Generated from: *{image_prompt}*",
            })
        else:
            answer = await query_ollama(user_message)
            return JSONResponse({"type": "text", "content": answer})
    except httpx.ConnectError as e:
        service = "ComfyUI" if "8188" in str(e) else "Ollama"
        return JSONResponse(
            {"type": "error", "content": f"Cannot connect to {service}. Make sure it is running."},
            status_code=502,
        )
    except Exception as e:
        return JSONResponse({"type": "error", "content": str(e)}, status_code=500)


# ── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
