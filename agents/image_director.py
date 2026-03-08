"""Image Director Agent — orchestrates the full image generation pipeline."""

from typing import Any

from agents.base import BaseAgent, AgentResult
from agents.prompt_engineer import PromptEngineerAgent


class ImageDirectorAgent(BaseAgent):
    """End-to-end image generation: prompt refinement → ComfyUI → result.

    Follows the ag-kit "agent chaining" pattern: calls PromptEngineer first,
    then uses the refined prompt to drive ComfyUI.
    """

    name = "image_director"
    description = "Orchestrates ComfyUI image generation with prompt enhancement"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.prompt_engineer = PromptEngineerAgent(
            ollama=self.ollama, comfyui=self.comfyui
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are an art director for AI image generation.\n"
            "You evaluate image requests and determine the best parameters.\n"
            "You work with Stable Diffusion 1.5 at 512x512 resolution.\n"
            "Keep responses concise and technical."
        )

    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        # Step 1: Extract the core image concept from the request
        raw_prompt = self._extract_subject(user_message)

        # Step 2: Chain to Prompt Engineer for SD-optimized prompt
        pe_result = await self.prompt_engineer.run(raw_prompt, target="image")
        enhanced_prompt = pe_result.content

        # Step 3: Generate image via ComfyUI
        try:
            image_b64 = await self.comfyui.generate_image(
                prompt=enhanced_prompt,
                width=kwargs.get("width", 512),
                height=kwargs.get("height", 512),
                steps=kwargs.get("steps", 20),
                cfg=kwargs.get("cfg", 7.0),
            )
        except Exception as e:
            return AgentResult(
                type="error",
                content=f"Image generation failed: {e}",
                agent_name=self.name,
            )

        return AgentResult(
            type="image",
            content=image_b64,
            agent_name=self.name,
            caption=f"🎨 Generated from: *{enhanced_prompt}*",
            metadata={
                "original_request": user_message,
                "enhanced_prompt": enhanced_prompt,
                "pipeline": ["prompt_engineer", "comfyui"],
            },
        )

    def _extract_subject(self, message: str) -> str:
        """Strip common command prefixes to get the core image subject."""
        keywords = [
            "draw", "generate image", "create image", "picture",
            "art", "illustration", "paint", "sketch", "make an image",
            "generate a picture", "create a picture", "render",
            "design", "visualize", "depict", "imagine an image",
            "show me", "create art",
        ]
        lower = message.lower()
        for kw in keywords:
            if kw in lower:
                idx = lower.find(kw)
                subject = message[idx + len(kw):].strip(" :.,!?-–—of")
                if subject:
                    return subject
        return message
