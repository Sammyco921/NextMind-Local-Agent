# core/tool_context.py
#
# NextMind v0.8 — Tool Execution Context
#
# Role:
#   Lightweight shared context object passed through pipeline stages.
#
# Purpose:
#   - Carry execution metadata
#   - Aggregate warnings
#   - Track runtime state
#   - Provide structured debugging visibility
#
# Non-goals:
#   - No memory system
#   - No planning logic
#   - No persistence layer
#   - No decision making


from __future__ import annotations

from typing import Dict, Any, List, Optional


# =====================================================
# TOOL CONTEXT
# =====================================================

class ToolContext:
    """
    Immutable-ish execution context container.
    """

    def __init__(self, goal: str):
        self.goal = goal

        # Execution tracking
        self.phase: str = "init"
        self.step_index: int = 0

        # Observability
        self.warnings: List[str] = []
        self.errors: List[str] = []

        # Runtime annotations
        self.metadata: Dict[str, Any] = {}

        # Execution trace (lightweight mirror of executor trace)
        self.trace: List[Dict[str, Any]] = []

    # =====================================================
    # PHASE CONTROL
    # =====================================================

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    # =====================================================
    # WARNING HANDLING
    # =====================================================

    def add_warning(self, warning: str) -> None:
        if warning:
            self.warnings.append(warning)

    def add_warnings(self, warnings: List[str]) -> None:
        for w in warnings:
            self.add_warning(w)

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    def add_error(self, error: str) -> None:
        if error:
            self.errors.append(error)

    # =====================================================
    # TRACE MANAGEMENT
    # =====================================================

    def add_trace(self, entry: Dict[str, Any]) -> None:
        self.trace.append(entry)

    # =====================================================
    # METADATA HANDLING
    # =====================================================

    def set_meta(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def get_meta(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    # =====================================================
    # SUMMARY EXPORT
    # =====================================================

    def snapshot(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "phase": self.phase,
            "step_index": self.step_index,
            "warnings": self.warnings,
            "errors": self.errors,
            "metadata": self.metadata,
            "trace": self.trace,
        }