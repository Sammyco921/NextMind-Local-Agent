from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


LIFECYCLE_STATES = frozenset({"active", "completed", "failed", "blocked", "abandoned"})


class Goal:
    def __init__(
        self,
        goal_id: str,
        description: str,
        lifecycle_state: str = "active",
        created_at: str | None = None,
        updated_at: str | None = None,
        parent_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.goal_id = goal_id
        self.description = description
        self.lifecycle_state = lifecycle_state
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.parent_id = parent_id

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "lifecycle_state": self.lifecycle_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_id": self.parent_id,
        }


class GoalRegistry:
    def __init__(self) -> None:
        self._goals: Dict[str, Goal] = {}

    def create_goal(
        self,
        description: str,
        parent_id: str | None = None,
    ) -> Goal:
        goal_id = uuid.uuid4().hex
        goal = Goal(goal_id=goal_id, description=description, parent_id=parent_id)
        self._goals[goal_id] = goal
        return goal

    def update_state(self, goal_id: str, state: str) -> None:
        if state not in LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle state: {state}")
        goal = self._goals.get(goal_id)
        if goal is None:
            return
        goal.lifecycle_state = state
        goal.updated_at = datetime.now(timezone.utc).isoformat()

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def list_goals(self) -> List[Goal]:
        return list(self._goals.values())
