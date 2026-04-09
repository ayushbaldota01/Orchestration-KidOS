"""Content Writer Agent — structured content generation."""

from typing import Any

from kidos.agents.base import BaseAgent, AgentResult


class ContentWriterAgent(BaseAgent):
    """Generates structured written content: articles, emails, docs, code, summaries.

    Follows the ag-kit behavioral-modes IMPLEMENT pattern: fast execution,
    production-ready output, minimal meta-commentary.
    """

    name = "content_writer"
    description = "Generates structured text content (articles, emails, code, docs)"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a skilled content writer and technical author.\n\n"
            "RULES:\n"
            "- Produce polished, ready-to-use content\n"
            "- Match the tone to the request (formal for docs, casual for blog, etc.)\n"
            "- Use markdown formatting for structure\n"
            "- For code: write complete, working code with no placeholders\n"
            "- For writing: be engaging, clear, and well-organized\n"
            "- DO NOT include meta-commentary like 'Here is your content:'\n"
            "- Output the content directly"
        )

    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        content = await self.think(user_message)
        return AgentResult(
            type="text",
            content=content,
            agent_name=self.name,
        )
