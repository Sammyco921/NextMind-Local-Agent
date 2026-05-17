from typing import Dict, Any, Callable


class ToolRegistry:
    """
    Schema-aware tool registry (typed version).
    """

    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    # -------------------------------------------------
    # REGISTER TOOL
    # -------------------------------------------------
    def register(
        self,
        name: str,
        func: Callable,
        args_schema: Dict[str, str],
        description: str = ""
    ):
        """
        args_schema format:
        {
            "filename": "str",
            "content": "str"
        }
        """

        self.tools[name] = {
            "func": func,
            "args_schema": args_schema,
            "description": description
        }

    # -------------------------------------------------
    # GET TOOL
    # -------------------------------------------------
    def get(self, name: str) -> Callable:
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        return self.tools[name]["func"]

    # -------------------------------------------------
    # VALIDATE ARGS (STRICT)
    # -------------------------------------------------
    def validate_args(self, name: str, args: dict):

        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")

        schema = self.tools[name]["args_schema"]

        # required keys
        for key in schema.keys():
            if key not in args:
                raise ValueError(f"{name} missing required arg: {key}")

        # reject unknown args
        for key in args:
            if key not in schema:
                raise ValueError(f"{name} got unexpected arg: {key}")

        return True

    # -------------------------------------------------
    # EXECUTE TOOL
    # -------------------------------------------------
    def run(self, name: str, args: dict):

        if name not in self.tools:
            return {"status": "fail", "error": f"Unknown tool: {name}"}

        try:
            self.validate_args(name, args)

            func = self.tools[name]["func"]
            result = func(**args)

            return {
                "status": "success",
                "output": result,
                "error": None
            }

        except Exception as e:
            return {
                "status": "fail",
                "output": None,
                "error": str(e)
            }

    # -------------------------------------------------
    # DEBUG HELP
    # -------------------------------------------------
    def list_tools(self):
        return {
            name: {
                "args": meta["args_schema"],
                "description": meta["description"]
            }
            for name, meta in self.tools.items()
        }
