from typing import Any
from kidos.tools.ollama_tool import OllamaTool
from kidos.core.logger import get_logger

logger = get_logger("kidos.core.task_router")

class TaskRouter:
    """KidOS Core: OS-Level Intelligent Task Router (PID 1 Orchestrator)"""

    def __init__(self, ollama: OllamaTool):
        self.ollama = ollama
        
        # Kernel rules for zero-shot process heuristics
        self._heuristics = {
            "image": ["draw", "generate image", "create image", "picture", "art", "illustration", "paint", "sketch", "show me", "create art"],
            "plan": ["plan", "break down", "step by step", "how to approach", "workflow for", "roadmap", "strategy for", "create a plan"],
            "research": ["explain", "why does", "how does", "compare", "analyze", "deep dive", "research", "pros and cons", "investigate"],
            "content": ["write", "draft", "compose", "create a post", "article", "blog", "summary", "document", "code", "email", "script", "implement"]
        }

    async def classify(self, message: str) -> str:
        """Determines which OS Subsystem (Agent) should handle the task."""
        lower = message.lower()

        # Phase 1: Heuristics Check (Fast Path)
        for category, keywords in self._heuristics.items():
            if any(kw in lower for kw in keywords):
                logger.info(f"TaskRouter heuristically fast-tracked task to Subsystem: [{category}]")
                return category

        # Phase 2: LLM Fallback (Deep Analysis)
        logger.info("TaskRouter falling back to semantic deep analysis for subsystem routing...")
        classification = await self.ollama.generate(
            prompt=(
                "You are the KidOS Kernel Task Router.\n"
                "Classify this user request into exactly ONE subsystem.\n"
                "Subsystems: image, plan, research, content, chat\n\n"
                f"Task: {message}\n\n"
                "Reply with ONLY the subsystem category name."
            ),
            system="Output exactly one word. You are a routing kernel.",
        )

        category = classification.strip().lower().rstrip(".")
        assigned = category if category in ("image", "plan", "research", "content", "chat") else "chat"
        logger.info(f"TaskRouter semantically assigned Subsystem: [{assigned}]")
        return assigned
