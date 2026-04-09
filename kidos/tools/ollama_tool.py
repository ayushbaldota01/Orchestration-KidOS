"""Ollama API wrapper — shared tool for all agents."""

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:7b-instruct"


class OllamaTool:
    """Stateless wrapper around the Ollama REST API."""

    def __init__(self, model: str = DEFAULT_MODEL, timeout: float = 120.0):
        self.model = model
        self.timeout = timeout

    async def generate(self, prompt: str, system: str = "") -> str:
        """Send a single prompt (with optional system message) and return the response text."""
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    async def chat(self, messages: list[dict], system: str = "") -> str:
        """Multi-turn chat. Each message: {"role": "user"|"assistant", "content": "..."}."""
        chat_messages = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        chat_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(OLLAMA_CHAT_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
