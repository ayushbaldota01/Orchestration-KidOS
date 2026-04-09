"""
KidOS v0.1 — AI Operating Environment Backend
FastAPI server with Executor Kernel + Vector Memory.
"""

from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kidos.core.executor import Executor
from kidos.core.model_registry import model_registry
from kidos.core.tool_registry import tool_registry
from kidos.memory.memory_engine import memory_engine

# ── Request / Response Models ────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="The user's chat message")


class ChatResponse(BaseModel):
    type: Literal["text", "image", "plan", "error"]
    content: str
    caption: str | None = None
    agent: str | None = None


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    n_results: int = Field(default=5, ge=1, le=20)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)


# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(title="KidOS", version="0.1.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent.parent / "static"), name="static")

# Shared tools (single instances, reused by all agents)
ollama = model_registry.get_model('default')
comfyui = tool_registry.get_tool('comfyui')
tts = tool_registry.get_tool('tts')

# The KidOS Executor kernel
executor = Executor(ollama=ollama, comfyui=comfyui, tts=tts)


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> HTMLResponse:
    html = (Path(__file__).parent.parent.parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/chat")
async def chat(body: ChatRequest) -> ChatResponse:
    """Route user message through the KidOS Executor pipeline."""
    user_message = body.message.strip()
    if not user_message:
        return ChatResponse(type="error", content="Empty message")

    try:
        result = await executor.run(user_message)
        return ChatResponse(
            type=result.type,
            content=result.content,
            caption=result.caption,
            agent=result.agent_name,
        )
    except httpx.ConnectError as e:
        service = "ComfyUI" if "8188" in str(e) else "Ollama"
        return ChatResponse(
            type="error",
            content=f"Cannot connect to {service}. Make sure it is running.",
        )
    except Exception as e:
        return ChatResponse(type="error", content=str(e))


# ── Memory API ───────────────────────────────────────────────────────────

@app.get("/memory/status")
async def memory_status():
    """Return the current state of the vector memory system."""
    return {
        "collection": "kidos_memory",
        "total_memories": memory_engine.count(),
        "backend": "ChromaDB (local)",
        "embedding_model": "nomic-embed-text (Ollama)",
    }


@app.post("/memory/search")
async def memory_search(body: MemorySearchRequest):
    """Search vector memory for relevant stored information."""
    try:
        results = await memory_engine.search(body.query, n_results=body.n_results)
        return {"query": body.query, "results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e), "results": [], "count": 0}


@app.post("/speak")
async def speak(body: SpeakRequest):
    """Trigger the server-side text-to-speech engine."""
    if not tts:
        return {"status": "error", "message": "TTS subsystem not initialized"}

    try:
        await tts.speak(body.text)
        return {"status": "success", "message": "Speech complete"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Fact Feed API ────────────────────────────────────────────────────────

FACT_SYSTEM_PROMPT = (
    "You are a fascinating fact generator for children and curious minds. "
    "Generate ONE truly surprising, mind-blowing, and short fact. "
    "The fact MUST be under 25 words. Do NOT include any preamble, "
    "numbering, or quotation marks. Just output the raw fact sentence."
)

IMAGE_PROMPT_SYSTEM = (
    "You are a Stable Diffusion prompt engineer. Given a fact, generate a "
    "SHORT, vivid image generation prompt (under 30 words) that would make "
    "a beautiful, vibrant vertical background image related to the fact. "
    "Output ONLY the prompt, no explanation. Focus on colors, lighting, "
    "and mood. Do NOT include any text or words in the image."
)


@app.post("/fact-feed/generate")
async def generate_fact():
    """Generate a random fact with an AI-generated background image."""
    from kidos.core.logger import get_logger
    logger = get_logger("kidos.api.fact_feed")

    try:
        # Step 1 — Generate a random fact via Ollama
        logger.info("Fact Feed: Generating random fact via Ollama...")
        fact = await ollama.generate(
            prompt="Give me a random surprising fact.",
            system=FACT_SYSTEM_PROMPT,
        )
        fact = fact.strip().strip('"').strip("'")
        logger.info("Fact Feed: Got fact: %s", fact)

        # Step 2 — Generate an image prompt from the fact
        logger.info("Fact Feed: Generating image prompt for background...")
        img_prompt = await ollama.generate(
            prompt=f"Generate a Stable Diffusion image prompt for this fact: {fact}",
            system=IMAGE_PROMPT_SYSTEM,
        )
        img_prompt = img_prompt.strip().strip('"').strip("'")
        logger.info("Fact Feed: Image prompt: %s", img_prompt)

        # Step 3 — Generate the background image via ComfyUI (9:16 vertical)
        logger.info("Fact Feed: Generating 512x912 image via ComfyUI...")
        image_data = await comfyui.generate_image(
            prompt=img_prompt,
            width=512,
            height=912,
            steps=20,
            cfg=7.5,
        )
        logger.info("Fact Feed: Image generated successfully.")

        return {
            "status": "success",
            "fact": fact,
            "image": image_data,
            "img_prompt": img_prompt,
        }

    except httpx.ConnectError as e:
        service = "ComfyUI" if "8188" in str(e) else "Ollama"
        logger.error("Fact Feed: Cannot connect to %s", service)
        return {
            "status": "error",
            "message": f"Cannot connect to {service}. Make sure it is running.",
        }
    except Exception as e:
        logger.error("Fact Feed: Error: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


# ── Library API ──────────────────────────────────────────────────────────

STORY_SYSTEM_PROMPT = (
    "You are a beloved children's story author. Generate a captivating, enchanting "
    "story for young children (ages 4-10). The story must have EXACTLY 5 pages. "
    "Each page should have 5-6 sentences with rich, vivid descriptions, dialogue, "
    "and emotional depth. Use colorful, imaginative language that paints pictures "
    "in the reader's mind. Include character names, sounds, and feelings. "
    "Output ONLY valid JSON in exactly this format, no other text:\n"
    '{"title":"Story Title","pages":['
    '{"text":"Page 1 text here."},'
    '{"text":"Page 2 text here."},'
    '{"text":"Page 3 text here."},'
    '{"text":"Page 4 text here."},'
    '{"text":"Page 5 text here."}'
    "]}"
)

ILLUSTRATION_SYSTEM = (
    "You are a Stable Diffusion prompt engineer for children's book illustrations. "
    "Given a page of a children's story, generate a SHORT image prompt (under 25 words) "
    "for a colorful, whimsical, child-friendly illustration. "
    "Style: digital art, storybook illustration, vibrant colors, soft lighting. "
    "Output ONLY the raw prompt. No explanation."
)


@app.post("/library/generate")
async def generate_book():
    """Generate a complete children's story book with illustrations."""
    import json as json_mod
    from kidos.core.logger import get_logger
    logger = get_logger("kidos.api.library")

    try:
        # Step 1 — Generate the story text via Ollama
        logger.info("Library: Generating story via Ollama...")
        raw_story = await ollama.generate(
            prompt="Write a magical, fun children's story about a topic you choose.",
            system=STORY_SYSTEM_PROMPT,
        )
        logger.info("Library: Raw story response: %s", raw_story[:200])

        # Parse JSON from the response (handle possible markdown wrapping)
        story_text = raw_story.strip()
        if story_text.startswith("```"):
            story_text = story_text.split("\n", 1)[-1]
            story_text = story_text.rsplit("```", 1)[0]
        story_text = story_text.strip()

        try:
            story = json_mod.loads(story_text)
        except json_mod.JSONDecodeError:
            # Try to extract JSON from the text
            start = story_text.find("{")
            end = story_text.rfind("}") + 1
            if start >= 0 and end > start:
                story = json_mod.loads(story_text[start:end])
            else:
                raise ValueError("Could not parse story JSON from Ollama response")

        title = story.get("title", "Untitled Story")
        pages = story.get("pages", [])
        if not pages:
            raise ValueError("Story has no pages")

        logger.info("Library: Story '%s' has %d pages", title, len(pages))

        # Step 2 — Generate a cover image
        logger.info("Library: Generating cover image...")
        cover_prompt = await ollama.generate(
            prompt=f"Generate a Stable Diffusion prompt for a children's book cover titled '{title}'",
            system=ILLUSTRATION_SYSTEM,
        )
        cover_prompt = cover_prompt.strip().strip('"').strip("'")
        cover_image = await comfyui.generate_image(
            prompt=cover_prompt + ", children's book cover, title page, vibrant",
            width=512,
            height=720,
            steps=20,
            cfg=7.5,
        )
        logger.info("Library: Cover image generated.")

        # Step 3 — Generate illustrations for each page
        illustrated_pages = []
        for i, page in enumerate(pages[:5]):
            page_text = page.get("text", "")
            logger.info("Library: Generating illustration for page %d...", i + 1)

            img_prompt = await ollama.generate(
                prompt=f"Generate an illustration prompt for this story page: {page_text}",
                system=ILLUSTRATION_SYSTEM,
            )
            img_prompt = img_prompt.strip().strip('"').strip("'")

            page_image = await comfyui.generate_image(
                prompt=img_prompt + ", children's book illustration, whimsical, colorful",
                width=512,
                height=512,
                steps=20,
                cfg=7.5,
            )

            illustrated_pages.append({
                "text": page_text,
                "image": page_image,
            })
            logger.info("Library: Page %d illustration done.", i + 1)

        logger.info("Library: Book '%s' fully generated with %d pages.", title, len(illustrated_pages))

        return {
            "status": "success",
            "title": title,
            "cover": cover_image,
            "pages": illustrated_pages,
        }

    except httpx.ConnectError as e:
        service = "ComfyUI" if "8188" in str(e) else "Ollama"
        logger.error("Library: Cannot connect to %s", service)
        return {
            "status": "error",
            "message": f"Cannot connect to {service}. Make sure it is running.",
        }
    except Exception as e:
        logger.error("Library: Error: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


# ── WonderTV API ─────────────────────────────────────────────────────────

FEED_IDEAS_SYSTEM = (
    "You are an educational children's video planner. Generate EXACTLY 4 unique video ideas "
    "for kids aged 5-12. Each video should be educational, inspiring, and value-driven. "
    "Topics can include: science wonders, nature, space, animals, history, kindness, "
    "creativity, health, world cultures, or life lessons. "
    "Output ONLY valid JSON, no other text:\n"
    '[{"title":"Video Title","description":"A 10-15 word engaging description"},'
    '{"title":"...","description":"..."},'
    '{"title":"...","description":"..."},'
    '{"title":"...","description":"..."}]'
)

THUMBNAIL_PROMPT_SYSTEM = (
    "You are a Stable Diffusion prompt engineer for YouTube-style video thumbnails. "
    "Given a video title and description, generate a SHORT (under 20 words) vivid prompt "
    "for a colorful, eye-catching, landscape-oriented thumbnail image. "
    "Style: vibrant digital art, cinematic lighting, no text, no words. "
    "Output ONLY the raw prompt."
)

VIDEO_SCRIPT_SYSTEM = (
    "You are an educational children's video script writer. Given a video title, "
    "write a EXACTLY 6-scene narration script. Each scene should have 3-4 sentences "
    "of engaging, educational narration suitable for a calm, low-stimulation video. "
    "Use a warm, friendly tone. Include interesting facts and wonder-inspiring content. "
    "Output ONLY valid JSON:\n"
    '[{"narration":"Scene 1 narration text here."},'
    '{"narration":"Scene 2 narration text here."},'
    '{"narration":"Scene 3 narration text here."},'
    '{"narration":"Scene 4 narration text here."},'
    '{"narration":"Scene 5 narration text here."},'
    '{"narration":"Scene 6 narration text here."}]'
)

SCENE_IMG_SYSTEM = (
    "You are a Stable Diffusion prompt engineer for calming educational video frames. "
    "Given a narration, generate a SHORT (under 20 words) prompt for a beautiful, "
    "calm, low-stimulation illustration. Style: soft watercolor, pastel colors, "
    "gentle lighting, serene atmosphere. No text, no words. Output ONLY the prompt."
)


class WonderTVRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(default="")


@app.post("/wondertv/generate-feed")
async def generate_feed():
    """Generate 4 video ideas with AI thumbnails for the WonderTV feed."""
    import json as json_mod
    from kidos.core.logger import get_logger
    logger = get_logger("kidos.api.wondertv")

    try:
        # Step 1 — Generate video ideas
        logger.info("WonderTV: Generating feed ideas...")
        raw = await ollama.generate(
            prompt="Generate 4 educational video ideas for children.",
            system=FEED_IDEAS_SYSTEM,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        raw = raw.strip()

        try:
            ideas = json_mod.loads(raw)
        except json_mod.JSONDecodeError:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                ideas = json_mod.loads(raw[start:end])
            else:
                raise ValueError("Could not parse feed ideas JSON")

        logger.info("WonderTV: Got %d ideas", len(ideas))

        # Step 2 — Generate thumbnails for each idea
        feed_items = []
        for i, idea in enumerate(ideas[:4]):
            title = idea.get("title", f"Video {i+1}")
            desc = idea.get("description", "")
            logger.info("WonderTV: Generating thumbnail for '%s'...", title)

            thumb_prompt = await ollama.generate(
                prompt=f"Generate a thumbnail prompt for: {title} - {desc}",
                system=THUMBNAIL_PROMPT_SYSTEM,
            )
            thumb_prompt = thumb_prompt.strip().strip('"').strip("'")

            thumbnail = await comfyui.generate_image(
                prompt=thumb_prompt + ", cinematic thumbnail, vibrant, landscape",
                width=512,
                height=288,
                steps=20,
                cfg=7.5,
            )

            feed_items.append({
                "title": title,
                "description": desc,
                "thumbnail": thumbnail,
            })
            logger.info("WonderTV: Thumbnail %d done.", i + 1)

        return {"status": "success", "feed": feed_items}

    except httpx.ConnectError as e:
        service = "ComfyUI" if "8188" in str(e) else "Ollama"
        return {"status": "error", "message": f"Cannot connect to {service}."}
    except Exception as e:
        logger.error("WonderTV feed error: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/wondertv/watch")
async def watch_video(body: WonderTVRequest):
    """Generate full video content: 6-scene script + images for playback."""
    import json as json_mod
    from kidos.core.logger import get_logger
    logger = get_logger("kidos.api.wondertv")

    try:
        # Step 1 — Generate the video script
        logger.info("WonderTV: Generating script for '%s'...", body.title)
        raw_script = await ollama.generate(
            prompt=f"Write a 6-scene educational video script about: {body.title}. {body.description}",
            system=VIDEO_SCRIPT_SYSTEM,
        )
        raw_script = raw_script.strip()
        if raw_script.startswith("```"):
            raw_script = raw_script.split("\n", 1)[-1].rsplit("```", 1)[0]
        raw_script = raw_script.strip()

        try:
            scenes = json_mod.loads(raw_script)
        except json_mod.JSONDecodeError:
            start = raw_script.find("[")
            end = raw_script.rfind("]") + 1
            if start >= 0 and end > start:
                scenes = json_mod.loads(raw_script[start:end])
            else:
                raise ValueError("Could not parse video script JSON")

        logger.info("WonderTV: Script has %d scenes", len(scenes))

        # Step 2 — Generate images for each scene
        video_scenes = []
        for i, scene in enumerate(scenes[:6]):
            narration = scene.get("narration", "")
            logger.info("WonderTV: Generating scene %d image...", i + 1)

            img_prompt = await ollama.generate(
                prompt=f"Generate an image prompt for this video scene: {narration}",
                system=SCENE_IMG_SYSTEM,
            )
            img_prompt = img_prompt.strip().strip('"').strip("'")

            scene_image = await comfyui.generate_image(
                prompt=img_prompt + ", calm educational illustration, soft colors",
                width=512,
                height=288,
                steps=20,
                cfg=7.5,
            )

            video_scenes.append({
                "narration": narration,
                "image": scene_image,
            })
            logger.info("WonderTV: Scene %d done.", i + 1)

        return {
            "status": "success",
            "title": body.title,
            "scenes": video_scenes,
        }

    except httpx.ConnectError as e:
        service = "ComfyUI" if "8188" in str(e) else "Ollama"
        return {"status": "error", "message": f"Cannot connect to {service}."}
    except Exception as e:
        logger.error("WonderTV watch error: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
