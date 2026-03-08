"""Base agent contract — all agents inherit from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from tools.ollama_tool import OllamaTool
from tools.comfyui_tool import ComfyUITool


@dataclass
class AgentResult:
    """Standardized output from every agent."""

    type: Literal["text", "image", "plan", "error"]
    content: str
    agent_name: str
    caption: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all NexusAI agents.

    Pattern extracted from ag-kit: each agent has a name, a system prompt
    (its "persona"), and access to shared tools.
    """

    name: str = "base"
    description: str = ""

    def __init__(
        self,
        ollama: OllamaTool | None = None,
        comfyui: ComfyUITool | None = None,
    ):
        self.ollama = ollama or OllamaTool()
        self.comfyui = comfyui or ComfyUITool()

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's persona injected as a system message into every LLM call."""

    @abstractmethod
    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        """Execute the agent's task and return a structured result."""

    async def think(self, prompt: str) -> str:
        """Convenience: call the LLM with this agent's system prompt."""
        return await self.ollama.generate(prompt, system=self.system_prompt)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
