"""Workflow Planner Agent — task decomposition for complex requests."""

from typing import Any

from agents.base import BaseAgent, AgentResult


class WorkflowPlannerAgent(BaseAgent):
    """Decomposes complex multi-step tasks into ordered, actionable plans.

    Pattern extracted from ag-kit project-planner: 4-phase workflow
    (Analysis → Planning → Solutioning → Implementation), simplified
    into a single-pass plan generation.
    """

    name = "workflow_planner"
    description = "Breaks complex tasks into step-by-step plans"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a workflow planner who decomposes complex tasks into clear steps.\n\n"
            "RULES:\n"
            "- Break the task into 3-8 ordered steps\n"
            "- Each step must be specific and actionable\n"
            "- Include expected output for each step\n"
            "- Identify which steps can run in parallel\n"
            "- Highlight dependencies between steps\n\n"
            "FORMAT:\n"
            "## Plan: [Brief Title]\n\n"
            "1. **Step name** — Description → Expected output\n"
            "2. **Step name** — Description → Expected output\n"
            "   ↳ Depends on: Step 1\n"
            "...\n\n"
            "### Summary\n"
            "Estimated complexity: [Low/Medium/High]\n"
            "Parallelizable steps: [list]\n"
        )

    async def run(self, user_message: str, **kwargs: Any) -> AgentResult:
        instruction = (
            f"Create a step-by-step plan for this task:\n\n{user_message}"
        )
        plan = await self.think(instruction)
        return AgentResult(
            type="plan",
            content=plan,
            agent_name=self.name,
        )
