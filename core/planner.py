import json

from core.llm import call_llm


PLANNER_SYSTEM_PROMPT = """
You are the Planner in an AI agent system.

Your job is to convert a user goal into a clear,
minimal step-by-step executable plan.

Rules:
- Break tasks into small executable steps
- Use ONLY available tools
- Do NOT execute steps yourself
- Do NOT explain reasoning
- Prefer simple solutions
- Every step must include:
    - id
    - tool
    - args

Available tools:
- write_file
- read_file
- list_dir

Return ONLY valid JSON.

Required JSON format:

{
  "goal": "...",
  "steps": [
    {
      "id": 1,
      "tool": "tool_name",
      "args": {
        ...
      }
    }
  ]
}
"""


class Planner:
    """
    Generates structured execution plans
    for the Orchestrator.
    """

    def __init__(self):
        pass

    # ========================================================
    # CREATE PLAN
    # ========================================================

    def create_plan(
        self,
        goal: str,
        previous_plan: dict = None
    ) -> dict:
        """
        Generate a structured execution plan.

        Args:
            goal (str):
                User objective.

            previous_plan (dict, optional):
                Previous failed plan for replanning.

        Returns:
            dict:
                Structured plan.
        """

        prompt = self._build_prompt(
            goal=goal,
            previous_plan=previous_plan
        )

        try:
            response = call_llm(
                prompt=prompt,
                system_prompt=PLANNER_SYSTEM_PROMPT
            )

            parsed = json.loads(response)

            return self._validate_plan(parsed)

        except json.JSONDecodeError:

            return {
                "goal": goal,
                "steps": [],
                "error": "Planner returned invalid JSON."
            }

        except Exception as e:

            return {
                "goal": goal,
                "steps": [],
                "error": str(e)
            }

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def _build_prompt(
        self,
        goal: str,
        previous_plan: dict = None
    ) -> str:
        """
        Build planner prompt.
        """

        prompt = f"""
User Goal:
{goal}
"""

        # ----------------------------------------------------
        # Include failed plan context if replanning
        # ----------------------------------------------------

        if previous_plan:

            prompt += f"""

Previous Plan Failed:
{json.dumps(previous_plan, indent=2)}

Generate a corrected plan.
"""

        return prompt

    # ========================================================
    # VALIDATE PLAN
    # ========================================================

    def _validate_plan(self, plan: dict) -> dict:
        """
        Validate planner output structure.
        """

        if "goal" not in plan:
            raise ValueError(
                "Plan missing 'goal' field."
            )

        if "steps" not in plan:
            raise ValueError(
                "Plan missing 'steps' field."
            )

        if not isinstance(plan["steps"], list):
            raise ValueError(
                "'steps' must be a list."
            )

        # ----------------------------------------------------
        # Validate each step
        # ----------------------------------------------------

        for step in plan["steps"]:

            if "id" not in step:
                raise ValueError(
                    "Step missing 'id'."
                )

            if "tool" not in step:
                raise ValueError(
                    "Step missing 'tool'."
                )

            if "args" not in step:
                raise ValueError(
                    "Step missing 'args'."
                )

        return plan
