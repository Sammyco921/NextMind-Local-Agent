# core/execution_context.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time


# =====================================================
# EXECUTION CONTEXT (v1.1)
# =====================================================

@dataclass
class ExecutionContext:
    """
    Global runtime state container.

    This is the single source of truth during execution.
    """

    goal: str
    start_time: float = field(default_factory=time.time)

    # ---------------------------------------------
    # DAG + EXECUTION STATE
    # ---------------------------------------------

    dag: Optional[Any] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)

    # ---------------------------------------------
    # RUNTIME TRACKING
    # ---------------------------------------------

    current_step: Optional[str] = None
    step_index: int = 0

    # ---------------------------------------------
    # EXECUTION METADATA
    # ---------------------------------------------

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------
    # ERROR TRACKING
    # ---------------------------------------------

    errors: List[str] = field(default_factory=list)

    # ---------------------------------------------
    # TRACE BUFFER (LIGHTWEIGHT)
    # ---------------------------------------------

    trace: List[Dict[str, Any]] = field(default_factory=list)

    # =================================================
    # STATE MUTATIONS
    # =================================================

    def add_step_trace(self, step: Dict[str, Any], result: Any, status: str):
        self.trace.append({
            "step": step,
            "result": result,
            "status": status,
            "timestamp": time.time()
        })

    def add_error(self, error: str):
        self.errors.append(error)

    def set_current_step(self, step_id: str):
        self.current_step = step_id
        self.step_index += 1

    # =================================================
    # SNAPSHOT
    # =================================================

    def snapshot(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "elapsed_time": time.time() - self.start_time,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "errors": self.errors,
            "trace_length": len(self.trace),
        }