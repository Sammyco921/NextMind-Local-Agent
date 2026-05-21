class ToolEnforcer:
    """
    Hard boundary validator for tool calls.
    Prevents semantic/parser mistakes from reaching execution.
    """

    def validate(self, tool_name: str, args: dict) -> dict:

        if tool_name in ["write_file", "read_file"]:

            filename = args.get("filename")

            if not isinstance(filename, str) or filename.strip() == "":
                filename = "output.txt"

            # kill instruction leakage
            if self._looks_like_instruction(filename):
                filename = "output.txt"

            args["filename"] = filename

        if tool_name == "write_file":

            content = args.get("content")

            if content is None:
                content = ""

            if not isinstance(content, str):
                content = str(content)

            args["content"] = content

        return {
            "tool": tool_name,
            "args": args
        }

    def _looks_like_instruction(self, text: str) -> bool:
        bad_signals = [
            "create a file",
            "generate a file",
            "write a file",
            "called",
            "containing"
        ]

        t = text.lower()
        return any(s in t for s in bad_signals)