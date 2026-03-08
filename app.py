"""
NexusAI – Agentic AI Chatbot Backend
FastAPI server with a Supervisor → Specialist Agent architecture.
"""

from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents.supervisor import SupervisorAgent
from tools.ollama_tool import OllamaTool
from tools.comfyui_tool import ComfyUITool

# ── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="The user's chat message")


class ChatResponse(BaseModel):
    type: Literal["text", "image", "plan", "error"]
    content: str
    caption: str | None = None
    agent: str | None = None


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="NexusAI Chatbot", version="2.0.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Shared tools (single instances, reused by all agents)
ollama = OllamaTool()
comfyui = ComfyUITool()

# The supervisor agent orchestrates everything
supervisor = SupervisorAgent(ollama=ollama, comfyui=comfyui)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> HTMLResponse:
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/chat")
async def chat(body: ChatRequest) -> ChatResponse:
    """Route user message through the Supervisor Agent pipeline."""
    user_message = body.message.strip()
    if not user_message:
        return ChatResponse(type="error", content="Empty message")

    try:
        result = await supervisor.run(user_message)
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


# ── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
