"""Research Agent — multi-step reasoning for complex questions."""

from typing import Any

from agents.base import BaseAgent, AgentResult


class ResearchAgent(BaseAgent):
    """Handles complex questions by breaking them into sub-queries.

    Uses a lightweight chain-of-thought pattern: the agent first plans
    its reasoning steps, then executes them sequentially, building
    context along the way.
    """

    name = "research"
    description = "Multi-step reasoning and chain-of-thought analysis"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a research analyst with expertise in breaking down complex topics.\n\n"
            "APPROACH:\n"
            "1. Identify the core question and any sub-questions\n"
            "2. Think through each sub-question systematically\n"
            "3. Synthesize findings into a clear, well-structured answer\n"
            "4. Cite your reasoning — explain HOW you arrived at conclusions\n\n"
            "STYLE:\n"
            "- Be thorough but concise\n"
            "- Use bullet points and headers for structure\n"
            "- Acknowledge uncertainty when appropriate\n"
            "- Provide actionable insights, not just information"
        )

    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        # Step 1: Ask the LLM to plan the research approach
        plan_prompt = (
            "I need to answer this question thoroughly. "
            "First, list 2-4 key sub-questions I should investigate:\n\n"
            f"Question: {user_message}\n\n"
            "List ONLY the sub-questions, numbered. No answers yet."
        )
        plan = await self.think(plan_prompt)

        # Step 2: Synthesize a comprehensive answer using the plan as context
        synthesis_prompt = (
            f"Original question: {user_message}\n\n"
            f"Research plan:\n{plan}\n\n"
            "Now provide a comprehensive, well-structured answer that addresses "
            "all aspects of the question. Use markdown formatting."
        )
        answer = await self.think(synthesis_prompt)

        return AgentResult(
            type="text",
            content=answer,
            agent_name=self.name,
            metadata={"research_plan": plan},
        )
