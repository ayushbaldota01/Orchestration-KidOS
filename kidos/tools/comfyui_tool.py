"""ComfyUI API wrapper — shared tool for image generation."""

import json
import time
import uuid
import base64
import asyncio
from pathlib import Path

import httpx

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_PROMPT_EP = f"{COMFYUI_URL}/prompt"
COMFYUI_HISTORY_EP = f"{COMFYUI_URL}/history"
COMFYUI_VIEW_EP = f"{COMFYUI_URL}/view"

DEFAULT_WORKFLOW = Path(__file__).parent.parent / "workflows" / "comfy_workflow.json"


class ComfyUITool:
    """Stateless wrapper around the ComfyUI REST API."""

    def __init__(
        self,
        workflow_path: Path = DEFAULT_WORKFLOW,
        timeout: float = 300.0,
        poll_interval: float = 1.0,
        max_polls: int = 300,
    ):
        self.workflow_path = workflow_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    async def generate_image(
        self,
        prompt: str,
        *,
        negative_prompt: str | None = None,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg: float = 7.0,
        seed: int | None = None,
    ) -> str:
        """Generate an image and return it as a data: URI (base64-encoded PNG)."""
        workflow = json.loads(self.workflow_path.read_text())

        # Patch workflow nodes
        workflow["3"]["inputs"]["seed"] = seed or (int(time.time()) % (2**32))
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["cfg"] = cfg
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        workflow["6"]["inputs"]["text"] = prompt

        if negative_prompt:
            workflow["7"]["inputs"]["text"] = negative_prompt

        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(COMFYUI_PROMPT_EP, json=payload)
            resp.raise_for_status()
            prompt_id = resp.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError("ComfyUI did not return a prompt_id")

            # Poll until complete
            for _ in range(self.max_polls):
                await asyncio.sleep(self.poll_interval)
                hist_resp = await client.get(f"{COMFYUI_HISTORY_EP}/{prompt_id}")
                if hist_resp.status_code != 200:
                    continue
                history = hist_resp.json()
                if prompt_id in history:
                    break
            else:
                raise RuntimeError("ComfyUI generation timed out")

            # Retrieve the image bytes
            outputs = history[prompt_id].get("outputs", {})
            for node_out in outputs.values():
                images = node_out.get("images", [])
                if images:
                    img = images[0]
                    params = {"filename": img["filename"], "type": img.get("type", "output")}
                    if img.get("subfolder"):
                        params["subfolder"] = img["subfolder"]

                    img_resp = await client.get(COMFYUI_VIEW_EP, params=params)
                    img_resp.raise_for_status()
                    b64 = base64.b64encode(img_resp.content).decode()
                    return f"data:image/png;base64,{b64}"

            raise RuntimeError("No image found in ComfyUI output")
