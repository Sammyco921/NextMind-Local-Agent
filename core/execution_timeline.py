from typing import Any, Dict, List


class ExecutionTimeline:
    """
    Records full DAG execution history across attempts.
    """

    def __init__(self):
        self.attempts: List[Dict[str, Any]] = []

    # =====================================================
    # RECORD ATTEMPT
    # =====================================================

    def record_attempt(self, dag, trace, status: str):

        self.attempts.append({
            "dag_snapshot": self._serialize_dag(dag),
            "trace": trace,
            "status": status,
            "diff": getattr(dag, "diff", None)
        })

    # =====================================================
    # DAG SERIALIZATION
    # =====================================================

    def _serialize_dag(self, dag):

        return {
            node_id: {
                "tool": node.tool,
                "args": node.args,
                "status": node.status,
                "depends_on": node.depends_on,
                "output": node.output,
                "error": node.error
            }
            for node_id, node in dag.nodes.items()
        }

    # =====================================================
    # CLI RENDER
    # =====================================================

    def render(self):

        print("\n==============================")
        print("EXECUTION TIMELINE")
        print("==============================")

        for i, attempt in enumerate(self.attempts):

            print(f"\n--- ATTEMPT {i + 1} ---")
            print(f"Status: {attempt['status']}")

            if attempt["diff"]:
                print("\nDiff:")
                print(attempt["diff"])

            print("\nTrace:")

            for t in attempt["trace"]:
                print(f"  {t}")