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

        return self._parse(raw)

    # ====================================================
    # PROMPT BUILDING
    # ====================================================

    def _build_prompt(self, goal, state):

        schema_text = self._format_schemas()
        history_text = self._format_history(state)

        return f"""
You are a deterministic planning engine.

You MUST output ONLY valid JSON.

NO explanations.
NO markdown.
NO extra text.
NO code fences.

---

OUTPUT FORMAT:

{{
  "steps": [
    {{
      "id": 0,
      "tool": "tool_name",
      "args": {{}}
    }}
  ]
}}

---

RULES:

- Use ONLY the tools listed below
- All arguments MUST be valid strings
- DO NOT output empty strings ("")
- DO NOT invent tools
- DO NOT include reasoning
- Return ONLY the next single best step

---

AVAILABLE TOOLS:

{schema_text}

---

GOAL:
{goal}

---

RECENT HISTORY (VERY IMPORTANT):

{history_text}

---

IMPORTANT BEHAVIOR RULES:

- If a previous step failed, DO NOT repeat it unchanged
- If a tool error occurred, adjust arguments or choose a different tool
- If the goal is already satisfied, prefer no further steps
- Keep steps minimal (one step only)

---

STATE:
{state}
""".strip()

    # ====================================================
    # TOOL SCHEMAS FORMAT
    # ====================================================

    def _format_schemas(self):

        lines = []

        for tool, spec in self.tool_schemas.items():

            lines.append(f"{tool}:")

            args = spec.get("args", {})
            required = set(spec.get("required", []))

            for arg, typ in args.items():
                req = "required" if arg in required else "optional"
                lines.append(f"  - {arg} ({typ}, {req})")

            lines.append("")

        return "\n".join(lines)

    # ====================================================
    # HISTORY FORMATTER (CRITICAL IMPROVEMENT)
    # ====================================================

    def _format_history(self, state):

        if not state or "history" not in state:
            return "No history"

        lines = []

        for item in state["history"][-5:]:  # last 5 only

            step = item.get("step", {})
            result = item.get("result", {})

            lines.append(
                f"STEP: {step.get('tool')} {step.get('args')}"
            )

            lines.append(
                f"RESULT: {result.get('status')} | {result.get('error') or result.get('output')}"
            )

        return "\n".join(lines) if lines else "No history"

    # ====================================================
    # PARSER (ROBUST + SAFE)
    # ====================================================

    def _parse(self, raw: str):

        if not raw or not isinstance(raw, str):
            raise RuntimeError("Planner returned empty response")

        raw = raw.strip()

        # remove accidental markdown
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw)

        except Exception:
            # fallback: try to extract JSON block
            data = self._extract_json_fallback(raw)

            if not data:
                raise RuntimeError(f"Invalid planner JSON:\n{raw}")

        if isinstance(data, list):
            data = {"steps": data}

        if "steps" not in data or not isinstance(data["steps"], list):
            raise RuntimeError(f"Planner missing valid steps:\n{raw}")

        normalized = []

        for i, step in enumerate(data["steps"]):

            if not isinstance(step, dict):
                continue

            tool = step.get("tool")
            args = step.get("args", {})

            if not tool:
                continue

            normalized.append({
                "id": step.get("id", i),
                "tool": tool,
                "args": args if isinstance(args, dict) else {}
            })

        if not normalized:
            raise RuntimeError("Planner produced no valid steps")

        return {"steps": normalized}

    # ====================================================
    # FALLBACK JSON EXTRACTION
    # ====================================================

    def _extract_json_fallback(self, text: str):

        start_obj = text.find("{")
        start_arr = text.find("[")

        if start_obj == -1 and start_arr == -1:
            return None

        start = start_arr if (start_arr != -1 and start_arr < start_obj) else start_obj

        open_c = "[" if start == start_arr else "{"
        close_c = "]" if open_c == "[" else "}"

        depth = 0

        for i in range(start, len(text)):

            if text[i] == open_c:
                depth += 1
            elif text[i] == close_c:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except Exception:
                        return None

        return None
