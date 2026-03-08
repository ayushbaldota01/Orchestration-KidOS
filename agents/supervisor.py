"""Supervisor Agent — task classification, routing, and response assembly.

This is the entry point for the agent layer. It:
1. Classifies the user's intent (keyword-first, LLM-fallback)
2. Routes to the correct specialist agent
3. Assembles the final response
"""

from __future__ import annotations

from typing import Any

from agents.base import BaseAgent, AgentResult
from agents.prompt_engineer import PromptEngineerAgent
from agents.image_director import ImageDirectorAgent
from agents.research_agent import ResearchAgent
from agents.content_writer import ContentWriterAgent
from agents.workflow_planner import WorkflowPlannerAgent
from tools.ollama_tool import OllamaTool
from tools.comfyui_tool import ComfyUITool


# ── Intent categories ──────────────────────────────────────────────────────

IMAGE_KEYWORDS = [
    "draw", "generate image", "create image", "picture",
    "art", "illustration", "paint", "sketch", "make an image",
    "generate a picture", "create a picture", "render",
    "visualize", "depict", "imagine an image", "show me", "create art",
]

PLAN_KEYWORDS = [
    "plan", "break down", "step by step", "how to approach",
    "create a plan", "workflow for", "roadmap", "decompose",
    "strategy for",
]

RESEARCH_KEYWORDS = [
    "explain", "why does", "how does", "compare", "analyze",
    "what is the difference", "pros and cons", "deep dive",
    "research", "investigate",
]

CONTENT_KEYWORDS = [
    "write", "draft", "compose", "create a post", "email",
    "article", "blog", "summary", "document", "report",
    "code", "function", "script", "implement",
]


class TaskRouter:
    """Two-stage intent classifier: keyword match → LLM fallback."""

    def __init__(self, ollama: OllamaTool):
        self.ollama = ollama

    async def classify(self, message: str) -> str:
        """Return one of: 'image', 'plan', 'research', 'content', 'chat'."""
        lower = message.lower()

        # Fast path: keyword matching (no LLM call needed)
        if any(kw in lower for kw in IMAGE_KEYWORDS):
            return "image"
        if any(kw in lower for kw in PLAN_KEYWORDS):
            return "plan"
        if any(kw in lower for kw in RESEARCH_KEYWORDS):
            return "research"
        if any(kw in lower for kw in CONTENT_KEYWORDS):
            return "content"

        # Slow path: ask the LLM to classify ambiguous requests
        classification = await self.ollama.generate(
            prompt=(
                "Classify this user message into exactly ONE category.\n"
                "Categories: image, plan, research, content, chat\n\n"
                "- image: user wants to generate/draw/create a picture\n"
                "- plan: user wants a step-by-step plan or workflow\n"
                "- research: user asks a complex analytical question\n"
                "- content: user wants written content (article, code, email)\n"
                "- chat: casual conversation or simple question\n\n"
                f"Message: {message}\n\n"
                "Reply with ONLY the category name, nothing else."
            ),
            system="You are a message classifier. Output only one word.",
        )

        category = classification.strip().lower().rstrip(".")
        return category if category in ("image", "plan", "research", "content", "chat") else "chat"


class SupervisorAgent(BaseAgent):
    """The brain of NexusAI's agent system.

    Patterns used (from ag-kit):
    - Orchestrator: decompose → select agent → invoke → synthesize
    - Task Router: keyword-first classification (fast path) + LLM fallback
    - Agent Boundary Enforcement: each agent stays in its lane
    - Context Chaining: results from one agent feed into the next
    """

    name = "supervisor"
    description = "Classifies requests and routes to specialist agents"

    def __init__(
        self,
        ollama: OllamaTool | None = None,
        comfyui: ComfyUITool | None = None,
    ):
        super().__init__(ollama=ollama, comfyui=comfyui)
        self.router = TaskRouter(self.ollama)

        # Initialize all specialist agents with shared tools
        self.agents: dict[str, BaseAgent] = {
            "image": ImageDirectorAgent(ollama=self.ollama, comfyui=self.comfyui),
            "plan": WorkflowPlannerAgent(ollama=self.ollama, comfyui=self.comfyui),
            "research": ResearchAgent(ollama=self.ollama, comfyui=self.comfyui),
            "content": ContentWriterAgent(ollama=self.ollama, comfyui=self.comfyui),
        }

    @property
    def system_prompt(self) -> str:
        return (
            "You are NexusAI, a helpful local AI assistant. "
            "Answer the user's question directly and concisely."
        )

    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        """Main entry point: classify → route → return result."""

        # Step 1: Classify intent
        intent = await self.router.classify(user_message)

        # Step 2: Route to specialist or handle directly
        if intent in self.agents:
            result = await self.agents[intent].run(user_message, **kwargs)
            return result

        # Default: simple chat (supervisor handles it directly)
        response = await self.think(user_message)
        return AgentResult(
            type="text",
            content=response,
            agent_name=self.name,
        )
