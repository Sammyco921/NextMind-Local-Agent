from typing import Dict, Any, List


# =====================================================
# EXECUTION CONTEXT
# =====================================================

class DAGExecutionContext:
    """
    Shared state across DAG execution steps.
    """

    def __init__(self):
        self.memory: Dict[str, Any] = {}


# =====================================================
# EXECUTION RESULT
# =====================================================

class ExecutionResult:
    def __init__(self, goal: str, status: str, trace: List[Dict[str, Any]]):
        self.goal = goal
        self.status = status
        self.trace = trace
        self.steps_executed = len(trace)

    def to_dict(self):
        return {
            "goal": self.goal,
            "status": self.status,
            "steps_executed": self.steps_executed,
            "trace": self.trace,
        }


# =====================================================
# DAG EXECUTOR (v1.1 CORE ENGINE)
# =====================================================

class DAGExecutor:

    def __init__(self, registry):
        self.registry = registry

    # -------------------------------------------------
    # MAIN ENTRYPOINT
    # -------------------------------------------------

    def execute(self, dag, goal: str):

        context = DAGExecutionContext()

        trace = []
        status = "success"

        nodes = getattr(dag, "nodes", [])

        for node in nodes:

            step_id = node.node_id
            tool_name = node.tool
            args = node.args or {}

            # -----------------------------------------
            # ARG RESOLUTION
            # -----------------------------------------
            resolved_args = self._resolve_args(args, context)

            try:
                # -------------------------------------
                # TOOL EXECUTION
                # -------------------------------------
                result = self.registry.run(tool_name, resolved_args)

                context.memory[step_id] = result

                trace.append({
                    "id": step_id,
                    "tool": tool_name,
                    "args": resolved_args,
                    "status": "success",
                    "result": result,
                    "note": None,
                })

            except Exception as e:

                status = "partial_failure"

                trace.append({
                    "id": step_id,
                    "tool": tool_name,
                    "args": resolved_args,
                    "status": "fail",
                    "result": {"error": str(e)},
                    "note": None,
                })

                break

        return ExecutionResult(goal, status, trace)

    # -------------------------------------------------
    # ARG RESOLVER (FIXED LOCATION)
    # -------------------------------------------------

    def _resolve_args(self, args: Dict[str, Any], context: DAGExecutionContext):

        """
        v1.1 minimal resolver (future-ready hook).

        Currently:
        - pass-through

        Future:
        - inject previous outputs
        - resolve templated dependencies
        """

        return args