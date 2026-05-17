import json
from typing import Dict, Any, List

from pydantic import BaseModel, ValidationError
from core.llm import call_llm


# ====================================================
# Pydantic Schemas (STRICT OUTPUT CONTRACT)
# ====================================================

class PlanStep(BaseModel):
    id: int
    tool: str
    args: Dict[str, Any]


class Plan(BaseModel):
    goal: str
    steps: List[PlanStep]


# ====================================================
# PLANNER
# ====================================================

class Planner:
    """
    Schema-enforced + self-repairing planner.

    Guarantees:
    - valid JSON output
    - valid structure (via Pydantic)
    - tool schema visibility from registry
    """

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry

    # ----------------------------------------------------
    # TOOL CONTEXT BUILDER
    # ----------------------------------------------------
    def _build_tool_context(self) -> str:
        lines = []

        for tool_name, meta in self.tool_registry.tools.items():
            schema = meta["args_schema"]

            lines.append(f"\nTool: {tool_name}")

            if not schema:
                lines.append("  args: none")
                continue

            lines.append("  args:")

            for arg_name, arg_type in schema.items():
                lines.append(f"    - {arg_name}: {arg_type}")

        return "\n".join(lines)

    # ----------------------------------------------------
    # SYSTEM PROMPT
    # ----------------------------------------------------
    def _build_prompt(self, goal: str) -> str:

        tool_context = self._build_tool_context()

        return f"""
You are a strict planning engine.

RULES:
- Output MUST be valid JSON only
- Must match schema EXACTLY
- Only use tools listed below
- Only use allowed argument names
- Do NOT invent arguments or tools

TOOLS:
{tool_context}

OUTPUT FORMAT:
{{
  "goal": "...",
  "steps": [
    {{
      "id": 1,
      "tool": "tool_name",
      "args": {{
        "arg": "value"
      }}
    }}
  ]
}}

GOAL:
{goal}
""".strip()

    # ----------------------------------------------------
    # CREATE PLAN (WITH AUTO REPAIR LOOP)
    # ----------------------------------------------------
    def create_plan(self, goal: str, max_retries: int = 2) -> Dict[str, Any]:

        last_error = None

        for attempt in range(max_retries + 1):

            prompt = self._build_prompt(goal)

            # inject repair feedback if needed
            if last_error:
                prompt += f"""

PREVIOUS OUTPUT WAS INVALID:

{last_error}

Fix it. Return ONLY valid JSON matching the schema.
"""

            raw = call_llm(prompt)

            # -----------------------------
            # STEP 1: JSON PARSE
            # -----------------------------
            try:
                data = json.loads(raw)

            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON: {str(e)}"
                continue

            # -----------------------------
            # STEP 2: STRUCTURE VALIDATION
            # -----------------------------
            try:
                plan = Plan(**data)
                return plan.model_dump()

            except ValidationError as e:
                last_error = str(e)
                continue

        # -----------------------------
        # FAILURE CASE
        # -----------------------------
        return {
            "status": "fail",
            "error": "Planner failed after max retries",
            "last_error": last_error
        }
