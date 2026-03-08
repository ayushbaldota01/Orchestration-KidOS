"""Prompt Engineer Agent — refines raw user text into optimized model-specific prompts."""

from typing import Any

from agents.base import BaseAgent, AgentResult


class PromptEngineerAgent(BaseAgent):
    """Transforms raw user requests into optimized prompts for downstream models.

    Used by other agents (especially ImageDirector) to improve output quality.
    """

    name = "prompt_engineer"
    description = "Refines prompts for Stable Diffusion or text generation quality"

    @property
    def system_prompt(self) -> str:
        return (
            "You are an expert prompt engineer specializing in AI model prompts.\n\n"
            "RULES:\n"
            "- When refining for Stable Diffusion: produce a comma-separated list of "
            "descriptive tags covering subject, style, lighting, mood, quality modifiers. "
            "Keep it under 100 words. Do NOT include negative prompts.\n"
            "- When refining for text generation: clarify intent, add context, "
            "specify output format.\n"
            "- Output ONLY the refined prompt. No explanations, no prefixes, no markdown."
        )

    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        target = kwargs.get("target", "image")  # "image" or "text"

        if target == "image":
            instruction = (
                "Refine this into a Stable Diffusion image generation prompt. "
                "Add artistic details, style, lighting, and quality tags. "
                "Output ONLY the prompt:\n\n"
                f"{user_message}"
            )
        else:
            instruction = (
                "Refine this into a clearer, more effective prompt for a text AI model. "
                "Output ONLY the refined prompt:\n\n"
                f"{user_message}"
            )

        refined = await self.think(instruction)
        return AgentResult(
            type="text",
            content=refined or user_message,
            agent_name=self.name,
            metadata={"target": target, "original": user_message},
        )
