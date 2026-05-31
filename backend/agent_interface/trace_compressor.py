from __future__ import annotations

from typing import Any, Dict, List

from agent_interface.contracts import TraceOutput
from execution_feed import build_result_summary, build_status_line, collect_steps, event_to_step
from core.memory.execution_memory_store import ExecutionMemoryStore


class TraceCompressor:
    """Standardizes execution results into human-readable output.

    Every execution produces:
    - a short summary ("Completed successfully" / "Failed at step X")
    - an optional step feed (human-readable only)
    - no structural execution metadata leakage
    """

    def __init__(self, execution_store: ExecutionMemoryStore) -> None:
        self._store = execution_store

    def compress(self, result_dict: Dict[str, Any]) -> TraceOutput:
        steps = collect_steps(self._store)
        summary = build_result_summary(result_dict)
        status_line = build_status_line(steps)
        return TraceOutput(
            summary=summary,
            status_line=status_line,
            steps=steps,
        )

    def get_steps(self) -> List[Dict[str, Any]]:
        return [event_to_step(e) for e in self._store.get_events()]

    def collect_steps_for_last_goal(self) -> List[Dict[str, Any]]:
        return collect_steps(self._store)
