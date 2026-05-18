import json


class Planner:

    def __init__(self, llm, tool_schemas):
        self.llm = llm
        self.tool_schemas = tool_schemas

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def create_plan(self, goal: str, state: dict = None):

        prompt = self._build_prompt(goal, state)

        raw = self.llm.generate(prompt)

        return self._parse_and_validate(raw)

    # ====================================================
    # PROMPT
    # ====================================================

    def _build_prompt(self, goal, state):

        schema_text = self._format_schemas()

        # 👇 THIS is where your rule MUST go
        strict_rules = """
CRITICAL RULES:
- Output ONLY JSON
- NO markdown
- NO explanations
- NO empty strings allowed
- ALL args must be non-empty valid strings
- DO NOT output empty strings. All args must be non-empty valid strings.
- Only use tools listed below
- Never invent tools or arguments
"""

        return f"""
You are a strict planning engine.

{strict_rules}

Return format:
{{
  "steps": [
    {{
      "id": 0,
      "tool": "tool_name",
      "args": {{}}
    }}
  ]
}}

AVAILABLE TOOLS:
{schema_text}

GOAL:
{goal}

STATE:
{state}
""".strip()

    # ====================================================
    # SCHEMA FORMATTER
    # ====================================================

    def _format_schemas(self):

        lines = []

        for tool, spec in self.tool_schemas.items():

            lines.append(f"{tool}:")

            args = spec.get("args", {})
            required = spec.get("required", [])

            for arg, typ in args.items():
                req = "required" if arg in required else "optional"
                lines.append(f"  - {arg} ({typ}, {req})")

            lines.append("")

        return "\n".join(lines)

    # ====================================================
    # PARSE + VALIDATE
    # ====================================================

    def _parse_and_validate(self, raw: str):

        raw = raw.strip()

        json_text = self._extract_json(raw)

        try:
            data = json.loads(json_text)

        except Exception as e:
            raise RuntimeError(f"Invalid JSON from planner: {e}\nRAW:\n{raw}")

        # ------------------------------------------------
        # STRUCTURE NORMALIZATION
        # ------------------------------------------------
        if isinstance(data, list):
            data = {"steps": data}

        if "steps" not in data:
            raise RuntimeError(f"Missing steps\nRAW:\n{raw}")

        if not isinstance(data["steps"], list):
            raise RuntimeError(f"'steps' must be a list\nRAW:\n{raw}")

        normalized = []

        for i, step in enumerate(data["steps"]):

            if not isinstance(step, dict):
                continue

            tool = step.get("tool")
            args = step.get("args", {})

            if not tool:
                continue

            if not isinstance(args, dict):
                continue

            # ------------------------------------------------
            # 🚨 HARD FILTER: NO EMPTY STRINGS
            # ------------------------------------------------
            cleaned_args = {}
            for k, v in args.items():

                if isinstance(v, str) and v.strip() == "":
                    continue  # drop empty strings

                cleaned_args[k] = v

            # ------------------------------------------------
            # TOOL VALIDATION
            # ------------------------------------------------
            if tool not in self.tool_schemas:
                continue

            schema = self.tool_schemas[tool]
            required = schema.get("required", [])

            # ensure required args exist AND are non-empty
            valid = True
            for req in required:
                if req not in cleaned_args:
                    valid = False
                elif isinstance(cleaned_args[req], str) and cleaned_args[req].strip() == "":
                    valid = False

            if not valid:
                continue

            normalized.append({
                "id": step.get("id", i),
                "tool": tool,
                "args": cleaned_args
            })

        if not normalized:
            raise RuntimeError("Planner produced no valid steps after validation")

        return {"steps": normalized}

    # ====================================================
    # JSON EXTRACTION
    # ====================================================

    def _extract_json(self, text: str):

        text = text.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        start_obj = text.find("{")
        start_arr = text.find("[")

        if start_obj == -1 and start_arr == -1:
            raise RuntimeError(f"No JSON found:\n{text}")

        if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
            start = start_arr
            open_c, close_c = "[", "]"
        else:
            start = start_obj
            open_c, close_c = "{", "}"

        depth = 0

        for i in range(start, len(text)):

            if text[i] == open_c:
                depth += 1
            elif text[i] == close_c:
                depth -= 1
                if depth == 0:
                    return text[start:i+1]

        raise RuntimeError(f"Unterminated JSON:\n{text}")
