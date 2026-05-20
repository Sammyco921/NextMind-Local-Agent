class IntentRouter:

    def __init__(self):
        pass

    def route(self, text: str):
        """
        Canonical entrypoint for intent detection.
        MUST always return structured intent object.
        """

        text = text.lower().strip()

        # -------------------------
        # FILE CREATE INTENT
        # -------------------------
        if any(x in text for x in ["create", "make", "generate", "write"]):
            if "file" in text or ".txt" in text or ".md" in text:
                return {
                    "intent": "file_create",
                    "all_intents": ["file_create"],
                    "confidence": 0.8
                }

        # -------------------------
        # FILE READ INTENT
        # -------------------------
        if any(x in text for x in ["read", "open", "show", "display"]):
            if "file" in text or ".txt" in text or ".md" in text:
                return {
                    "intent": "file_read",
                    "all_intents": ["file_read"],
                    "confidence": 0.8
                }

        # -------------------------
        # DIRECTORY LISTING
        # -------------------------
        if any(x in text for x in ["list", "files", "directory", "folder"]):
            return {
                "intent": "list_dir",
                "all_intents": ["list_dir"],
                "confidence": 0.7
            }

        # -------------------------
        # UNKNOWN
        # -------------------------
        return {
            "intent": "unknown",
            "all_intents": [],
            "confidence": 0.3
        }