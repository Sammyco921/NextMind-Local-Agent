# core/step_normalizer.py


class StepNormalizer:

    def normalize(self, step: dict) -> dict:
        """
        Ensures tool steps are valid before execution.
        """

        tool = step.get("tool")
        args = step.get("args", {})

        if not tool:
            raise ValueError("Missing tool in step")

        # -------------------------
        # WRITE FILE FIX
        # -------------------------
        if tool == "write_file":

            filename = args.get("filename")
            content = args.get("content", "")

            if not filename or not isinstance(filename, str):
                raise ValueError(f"Invalid filename: {filename}")

            if content is None:
                content = ""

            return {
                "tool": tool,
                "args": {
                    "filename": filename.strip(),
                    "content": content
                }
            }

        # -------------------------
        # READ FILE FIX
        # -------------------------
        if tool == "read_file":
            filename = args.get("filename")

            if not filename:
                raise ValueError("Missing filename")

            return step

        # default passthrough
        return step