from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.memory.agent_context_api import AgentContextAPI
from core.memory.goal_registry import GoalRegistry

if TYPE_CHECKING:
    from core.strict_pipeline import StrictPipeline


class AgentLoopController:
    """Deterministic agent loop: observe → interpret → propose → (optional execute).

    No autonomy. No background execution. Each step is manually triggered.
    """

    def __init__(
        self,
        api: AgentContextAPI,
        goal_registry: GoalRegistry | None = None,
        pipeline: StrictPipeline | None = None,
    ) -> None:
        self._api = api
        self._goals = goal_registry
        self._pipeline = pipeline

    def observe(
        self,
        goal_ids: Optional[List[str]] = None,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        return self._api.get_context(
            goal_ids=goal_ids,
            time_window_hours=time_window_hours,
        )

    def interpret(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ctx = context.get("context", context)
        active_raw = ctx.get("active_goals", [])
        blockers_raw = ctx.get("blockers", [])
        exec_summary = ctx.get("execution_summary", {})
        decisions_raw = ctx.get("relevant_decisions", [])

        failed_goal_ids = {b["goal_id"] for b in blockers_raw}
        active_goals = [
            {
                "goal_id": g["goal_id"],
                "description": g["description"],
                "status": g["status"],
            }
            for g in active_raw
        ]

        blocked_goals = [
            {
                "goal_id": b["goal_id"],
                "reason": b["reason"],
            }
            for b in blockers_raw
        ]

        recent_failures = [
            {
                "node_id": f["node_id"],
                "error": f["error"],
                "count": f["count"],
            }
            for f in exec_summary.get("failures", [])
        ]

        decision_pressure_points = []
        for d in decisions_raw:
            gid = d.get("goal_id", "")
            if gid in failed_goal_ids or any(
                dpt["decision_point"] == "goal_failed" or dpt["decision_point"] == "goal_blocked"
                for dpt in decisions_raw
            ):
                decision_pressure_points.append({
                    "goal_id": gid,
                    "decision_point": d.get("decision_point", ""),
                    "rationale": d.get("rationale"),
                    "selected": d.get("selected", ""),
                })

        total_nodes = len(exec_summary.get("recent_nodes", []))
        total_failures = sum(f["count"] for f in recent_failures)
        success_count = total_nodes - total_failures
        health_ratio = success_count / max(total_nodes, 1)

        execution_health = {
            "total_nodes_tracked": total_nodes,
            "total_failures": total_failures,
            "success_ratio": round(health_ratio, 2),
        }

        return {
            "active_goals": active_goals,
            "blocked_goals": blocked_goals,
            "recent_failures": recent_failures,
            "decision_pressure_points": decision_pressure_points,
            "execution_health": execution_health,
        }

    def propose_next_action(
        self, agent_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        blocked = agent_state.get("blocked_goals", [])
        active = agent_state.get("active_goals", [])
        failures = agent_state.get("recent_failures", [])

        goal_id: str | None = None
        action_type: str = "noop"
        reason: str = "No actionable state detected"
        confidence: float = 1.0
        dependencies: List[str] = []

        if blocked:
            goal_id = blocked[0]["goal_id"]
            if failures:
                action_type = "retry"
                reason = f"Goal {goal_id} is blocked due to execution failures"
                confidence = 0.7
                dependencies = [f["node_id"] for f in failures[:3]]
            else:
                action_type = "unblock"
                reason = f"Goal {goal_id} is blocked with reason: {blocked[0]['reason']}"
                confidence = 0.5
        elif active:
            goal_id = active[0]["goal_id"]
            action_type = "continue"
            reason = f"Goal {goal_id} is active with no blockers — ready to proceed"
            confidence = 0.9
        else:
            goal_id = None
            action_type = "noop"
            reason = "No active or blocked goals found"

        return {
            "goal_id": goal_id,
            "action_type": action_type,
            "reason": reason,
            "confidence": confidence,
            "dependencies": dependencies,
        }

    def execute(self, action_proposal: Dict[str, Any]) -> Dict[str, Any]:
        if self._pipeline is None:
            return {"status": "skipped", "reason": "No pipeline available for execution"}

        goal_id = action_proposal.get("goal_id")
        if not goal_id:
            return {"status": "skipped", "reason": "No goal_id in action proposal"}

        action = action_proposal.get("action_type", "noop")
        if action == "noop":
            return {"status": "skipped", "reason": "No-op action, nothing to execute"}

        description: str | None = None
        if self._goals is not None:
            g = self._goals.get_goal(goal_id)
            if g is not None:
                description = g.description

        if not description:
            return {"status": "failed", "reason": f"Goal {goal_id} not found in registry"}

        result = self._pipeline.run(description)
        return {
            "status": "completed" if result.status == "success" else "failed",
            "goal_id": goal_id,
            "description": description,
            "pipeline_status": result.status,
        }
