# core/orchestrator.py
#
# NextMind v0.7 — Orchestrator (Final Wiring Layer)
#
# This is the single entrypoint for the system.
#
# It enforces the full pipeline:
#   Planner → Validator → Scheduler → Executor
#
# Each stage is strictly isolated.
# Failures are captured with phase metadata.


from __future__ import annotations

from typing import Any, Dict

from core.pipeline_validator import PipelineValidator
from core.scheduler import Scheduler
from core.executor import Executor


class Orchestrator:
    """
    v0.7 Orchestrator

    The only public entrypoint for running a goal.
    """

    def __init__(self, planner, registry):
        self.planner   = planner
        self.validator = PipelineValidator()
        self.scheduler = Scheduler()
        self.executor  = Executor(registry)

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def run(self, goal: str) -> Dict[str, Any]:

        # -------------------------------------------------
        # 1. PLANNING
        # -------------------------------------------------
        try:
            raw_steps = self.planner.plan(goal)

            if not isinstance(raw_steps, list):
                return self._fail(goal, "planning", "Planner did not return a list")

        except Exception as e:
            return self._fail(goal, "planning", str(e))

        # -------------------------------------------------
        # 2. VALIDATION
        # -------------------------------------------------
        try:
            validated_steps = self.validator.validate(raw_steps)

        except Exception as e:
            return self._fail(goal, "validation", str(e))

        # -------------------------------------------------
        # 3. SCHEDULING
        # -------------------------------------------------
        try:
            scheduled_steps = self.scheduler.schedule(validated_steps)

        except Exception as e:
            return self._fail(goal, "scheduling", str(e))

        # -------------------------------------------------
        # 4. EXECUTION
        # -------------------------------------------------
        try:
            result = self.executor.execute(goal, scheduled_steps)

        except Exception as e:
            return self._fail(goal, "execution", str(e))

        # -------------------------------------------------
        # FINAL RESULT
        # -------------------------------------------------
        return result.to_dict()

    # =====================================================
    # UNIFIED ERROR FORMAT
    # =====================================================

    def _fail(self, goal: str, phase: str, error: str) -> Dict[str, Any]:
        return {
            "goal": goal,
            "status": "fail",
            "steps_executed": 0,
            "history": [],
            "phase": phase,
            "error": error,
        }