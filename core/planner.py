import re
import json


class Planner:
    """
    Stable Planner v0.6.2

    Responsibilities:
    - detect intent (write/read/list/multi-step)
    - preserve structured data (JSON safe)
    - expand multi-file tasks correctly
    - output deterministic tool steps
    """

    def __init__(self, intent_router=None):
        self.intent_router = intent_router

    # ====================================================
    # MAIN ENTRY
    # ====================================================
    def plan(self, goal: str):

        goal = goal.strip()

        # optional external router hook
        if self.intent_router:
            try:
                routed = self.intent_router.route(goal)
                if routed:
                    return routed
            except Exception:
                pass

        # 1. MULTI-STEP DETECTION
        if self._is_sequence(goal):
            return self._plan_sequence(goal)

        # 2. MULTI-FILE DETECTION
        if self._is_multi_file(goal):
            return self._plan_multi_file(goal)

        # 3. JSON DETECTION
        if self._has_json(goal):
            return self._plan_json(goal)

        # 4. DEFAULT SINGLE STEP
        return [self._plan_single(goal)]

    # ====================================================
    # SEQUENCES
    # ====================================================
    def _is_sequence(self, text):
        return any(k in text.lower() for k in [" then ", " after that ", " and then "])

    def _plan_sequence(self, text):

        parts = re.split(r"\bthen\b|\band then\b|\bafter that\b", text, flags=re.I)

        return [
            self._plan_single(p.strip())
            for p in parts
            if p.strip()
        ]

    # ====================================================
    # MULTI FILE
    # ====================================================
    def _is_multi_file(self, text):
        return "file" in text.lower() and "," in text

    def _plan_multi_file(self, text):

        files = re.findall(r"([a-zA-Z0-9_\-]+\.(md|json|txt))", text)

        if not files:
            return [self._plan_single(text)]

        steps = []

        for f in files:
            filename = f[0]

            header = f"# {filename.split('.')[0]}"

            steps.append({
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": header
                }
            })

        return steps

    # ====================================================
    # JSON HANDLING (FIXED PROPERLY)
    # ====================================================
    def _has_json(self, text):
        return "{" in text and "}" in text

    def _extract_json(self, text):
        try:
            match = re.search(r"\{.*\}", text)
            if not match:
                return None
            return json.loads(match.group(0))
        except Exception:
            return None

    def _plan_json(self, text):

        data = self._extract_json(text)
        filename = self._extract_filename(text, "data.json")

        if not data:
            return [self._plan_single(text)]

        return [{
            "tool": "write_file",
            "args": {
                "filename": filename,
                "content": json.dumps(data)
            }
        }]

    # ====================================================
    # SINGLE STEP (CORE FIXED ROUTING)
    # ====================================================
    def _plan_single(self, text):

        t = text.lower()

        filename = self._extract_filename(text)
        content = self._extract_content(text)

        # WRITE FILE
        if any(k in t for k in ["create", "write", "make", "generate", "file"]):
            return {
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": content
                }
            }

        # READ FILE
        if any(k in t for k in ["read", "show", "open"]):
            return {
                "tool": "read_file",
                "args": {
                    "filename": filename
                }
            }

        # LIST DIRECTORY
        return {
            "tool": "list_dir",
            "args": {}
        }

    # ====================================================
    # HELPERS (FIXED EXTRACTION LOGIC)
    # ====================================================
    def _extract_filename(self, text, default="output.txt"):

        match = re.search(r"([a-zA-Z0-9_\-]+\.(md|json|txt))", text)
        return match.group(1) if match else default

    def _extract_content(self, text):

        # strongest: quoted strings first
        quoted = re.findall(r'"(.*?)"', text)
        if quoted:
            return quoted[-1]

        # fallback cleanup
        cleaned = re.sub(
            r"(create|write|make|generate|file|called|containing|with|content)",
            "",
            text,
            flags=re.I
        )

        return cleaned.strip() or ""