# core/scheduler.py
#
# NextMind v0.7 — Scheduler
#
# Role:
#   Convert validated steps into a deterministic execution order.
#
# Guarantees:
#   - Pure dependency ordering (DAG → linear list)
#   - No reordering after validation
#   - No execution logic
#   - No semantic interpretation
#
# Output:
#   List[ScheduledStep] (same dicts, ordered for execution)


from __future__ import annotations

from typing import List, Dict, Any
from collections import defaultdict, deque


class SchedulerError(Exception):
    pass


class Scheduler:
    """
    Deterministic topological scheduler.
    """

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def schedule(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not steps:
            raise SchedulerError("Scheduler: empty step list")

        # -----------------------------
        # Index steps
        # -----------------------------
        indexed = {}
        graph = defaultdict(list)
        indegree = defaultdict(int)

        for i, step in enumerate(steps):
            step_id = f"step_{i}"
            step["_id"] = step_id
            indexed[step_id] = step

            indegree[step_id] = 0

        # -----------------------------
        # Build dependency graph
        # -----------------------------
        for step_id, step in indexed.items():
            deps = step.get("depends_on", [])

            for dep in deps:
                if dep not in indexed:
                    raise SchedulerError(
                        f"Scheduler: missing dependency '{dep}' for {step_id}"
                    )

                graph[dep].append(step_id)
                indegree[step_id] += 1

        # -----------------------------
        # Topological sort (Kahn's algorithm)
        # -----------------------------
        queue = deque([sid for sid, deg in indegree.items() if deg == 0])
        ordered: List[str] = []

        while queue:
            current = queue.popleft()
            ordered.append(current)

            for neighbor in graph[current]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        # -----------------------------
        # Cycle detection
        # -----------------------------
        if len(ordered) != len(indexed):
            raise SchedulerError("Scheduler: cycle detected in dependency graph")

        # -----------------------------
        # Build final schedule
        # -----------------------------
        return [indexed[sid] for sid in ordered]

    # =====================================================
    # OPTIONAL DEBUG HELPERS
    # =====================================================

    def explain(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Returns a human-readable dependency graph for debugging.
        """
        explanation = {
            "nodes": len(steps),
            "edges": [],
        }

        for i, step in enumerate(steps):
            sid = f"step_{i}"
            for dep in step.get("depends_on", []):
                explanation["edges"].append((dep, sid))

        return explanation