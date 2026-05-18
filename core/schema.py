from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


# ====================================================
# STEP STRUCTURE
# ====================================================

@dataclass
class Step:
    id: int
    tool: str
    args: Dict[str, Any]


# ====================================================
# EXECUTION RESULT STRUCTURE
# ====================================================

@dataclass
class StepResult:
    status: str  # "success" | "fail" | "fatal_error"
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    fix: Optional[str] = None
    step: Optional[Step] = None


# ====================================================
# HISTORY ENTRY
# ====================================================

@dataclass
class HistoryEntry:
    step: Step
    result: StepResult
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ====================================================
# FULL STATE MODEL
# ====================================================

@dataclass
class State:
    goal: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    history: List[HistoryEntry] = field(default_factory=list)

    steps_executed: int = 0
    failure_count: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)


# ====================================================
# STATE BUILDER (FACTORY)
# ====================================================

def create_state(goal: str) -> State:
    return State(goal=goal)


# ====================================================
# STATE HELPERS
# ====================================================

def add_history(state: State, step: Step, result: StepResult):
    state.history.append(
        HistoryEntry(step=step, result=result)
    )
    state.steps_executed = len(state.history)


def last_result(state: State) -> Optional[StepResult]:
    if not state.history:
        return None
    return state.history[-1].result


def last_step(state: State) -> Optional[Step]:
    if not state.history:
        return None
    return state.history[-1].step
