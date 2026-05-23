import re


class SemanticParser:

    def parse(self, goal: str) -> dict:

        goal = self._normalize(goal)

        intent = self._detect_intent(goal)

        if intent == "file_read":
            filename, missing = self._safe_extract_filename(goal)

            return {
                "intent": "file_read",
                "tool": "read_file",
                "args": {
                    "filename": filename
                },
                "missing": missing
            }

        if intent == "list_dir":
            return {
                "intent": "list_dir",
                "tool": "list_dir",
                "args": {},
                "missing": []
            }

        if intent == "file_create":

            filename, missing_f = self._safe_extract_filename(goal)
            content, missing_c = self._safe_extract_content(goal)

            return {
                "intent": "file_create",
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": content
                },
                "missing": missing_f + missing_c
            }

        return {
            "intent": "unknown",
            "tool": "list_dir",
            "args": {},
            "missing": []
        }

    # ====================================================
    # INTENT
    # ====================================================
    def _detect_intent(self, text: str) -> str:
        t = text.lower()

        if any(x in t for x in ["read", "open", "show"]):
            return "file_read"

        if any(x in t for x in ["list", "directory", "files"]):
            return "list_dir"

        if any(x in t for x in ["create", "generate", "make", "write"]):
            return "file_create"

        return "unknown"

    # ====================================================
    # NORMALIZATION
    # ====================================================
    def _normalize(self, text: str) -> str:
        text = text.strip()
        text = text.replace("“", "\"").replace("”", "\"")
        text = text.replace("‘", "'").replace("’", "'")
        return text

    # ====================================================
    # FILE NAME (SAFE)
    # ====================================================
    def _safe_extract_filename(self, text: str):
        text = self._isolate_instruction(text)

        match = re.search(r"\b[\w\-. ]+\.(txt|md|json|py)\b", text)
        if match:
            return match.group(0), []

        return "output.txt", ["filename"]

    # ====================================================
    # CONTENT (SAFE)
    # ====================================================
    def _safe_extract_content(self, text: str):
        text = self._isolate_instruction(text)

        quoted = re.findall(r"\"(.*?)\"", text)
        if quoted:
            return quoted[0], []

        smart = re.findall(r"[“”](.*?)[“”]", text)
        if smart:
            return smart[0], []

        if "containing" in text.lower():
            parts = re.split(r"containing", text, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[-1].strip():
                return parts[-1].strip(" ."), []

        return "", ["content"]

    # ====================================================
    # ISOLATION
    # ====================================================
    def _isolate_instruction(self, text: str) -> str:
        splitters = [" with ", " containing ", " that ", " then ", " and "]

        lower = text.lower()

        for s in splitters:
            if s in lower:
                return text.split(s)[0].strip()

        return text