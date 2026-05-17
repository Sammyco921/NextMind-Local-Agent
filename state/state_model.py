from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class TaskState:
    """
    Central runtime state object for NextMind.

    Tracks:
    - current task
    - execution progress
    - retries
    - logs
    - system status
    """

    # ========================================================
    # CORE TASK INFO
    # ========================================================

    task_id: str
    goal: str

    status: str = "CREATED"

    # ========================================================
    # PLAN DATA
    # ========================================================

    plan: List[Dict[str, Any]] = field(default_factory=list)

    current_step_index: int = 0

    # ========================================================
    # EXECUTION TRACKING
    # ========================================================

    completed_steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    failed_steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    retry_count: int = 0
    replan_count: int = 0

    # ========================================================
    # LOGGING
    # ========================================================

    logs: List[str] = field(default_factory=list)

    created_at: str = field(
        default_factory=lambda:
        datetime.utcnow().isoformat()
    )

    updated_at: str = field(
        default_factory=lambda:
        datetime.utcnow().isoformat()
    )

    # ========================================================
    # LOG MANAGEMENT
    # ========================================================

    def add_log(self, message: str):
        """
        Add timestamped log entry.
        """

        timestamp = datetime.utcnow().isoformat()

        entry = f"[{timestamp}] {message}"

        self.logs.append(entry)

        self.updated_at = timestamp

    # ========================================================
    # STATUS MANAGEMENT
    # ========================================================

    def set_status(self, status: str):
        """
        Update task status.
        """

        self.status = status

        self.updated_at = datetime.utcnow().isoformat()

    # ========================================================
    # STEP TRACKING
    # ========================================================

    def add_completed_step(
        self,
        step: Dict[str, Any]
    ):
        """
        Record completed step.
        """

        self.completed_steps.append(step)

        self.updated_at = datetime.utcnow().isoformat()

    def add_failed_step(
        self,
        step: Dict[str, Any]
    ):
        """
        Record failed step.
        """

        self.failed_steps.append(step)

        self.updated_at = datetime.utcnow().isoformat()

    # ========================================================
    # PLAN MANAGEMENT
    # ========================================================

    def set_plan(
        self,
        plan: List[Dict[str, Any]]
    ):
        """
        Store execution plan.
        """

        self.plan = plan

        self.updated_at = datetime.utcnow().isoformat()

    def get_current_step(self):
        """
        Retrieve current step safely.
        """

        if (
            self.current_step_index < len(self.plan)
        ):
            return self.plan[self.current_step_index]

        return None

    def advance_step(self):
        """
        Move to next step.
        """

        self.current_step_index += 1

        self.updated_at = datetime.utcnow().isoformat()

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state object into dictionary.
        """

        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status,
            "plan": self.plan,
            "current_step_index": self.current_step_index,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "retry_count": self.retry_count,
            "replan_count": self.replan_count,
            "logs": self.logs,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
