# core/constraints_engine.py
#
# NextMind v0.8 — Constraints Engine (Integrated Gatekeeper)
#
# Role:
#   Deterministic rule evaluator + execution gate.
#
# Upgrade from v0.7:
#   - Now supports pre-execution gating decisions
#   - Can attach warnings into pipeline metadata
#   - Provides strict block signal for executor
#
# Non-goals:
#   - No planning
#   - No scheduling
#   - No tool execution
#   - No semantic interpretation


from __future__ import annotations

from typing import Dict, Any, List, Optional


# =====================================================
# RESULT TYPE
# =====================================================

class ConstraintResult:
    """
    Outcome of constraint evaluation.
    """

    def __init__(
        self,
        allowed: bool,
        reason: str = "",
        warnings: Optional[List[str]] = None,
        annotations: Optional[Dict[str, Any]] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.warnings = warnings or []
        self.annotations = annotations or {}

    def to_dict(self) -> Dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "warnings": self.warnings,
            "annotations": self.annotations,
        }


# =====================================================
# CONSTRAINT ENGINE
# =====================================================

class ConstraintsEngine:
    """
    Deterministic rule evaluator.

    Now acts as a *pre-execution gate*.
    """

    def __init__(self):
        self.blocked_tools = set()
        self.blocked_scopes = set()
        self.max_chain_length = None

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def evaluate(
        self,
        step: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ConstraintResult:

        context = context or {}

        tool = step.get("tool")
        scope = step.get("scope")
        risk = step.get("risk")
        side_effects = step.get("side_effects")

        warnings: List[str] = []
        annotations: Dict[str, Any] = {}

        # -------------------------------------------------
        # TOOL BLOCK LIST (hard stop)
        # -------------------------------------------------
        if tool in self.blocked_tools:
            return ConstraintResult(
                allowed=False,
                reason=f"Blocked tool: {tool}",
            )

        # -------------------------------------------------
        # SCOPE BLOCK LIST (hard stop)
        # -------------------------------------------------
        if scope in self.blocked_scopes:
            return ConstraintResult(
                allowed=False,
                reason=f"Blocked scope: {scope}",
            )

        # -------------------------------------------------
        # RISK SIGNALING (non-blocking by default)
        # -------------------------------------------------
        if risk == "high":
            warnings.append("High-risk operation detected")
            annotations["risk_flag"] = True

        # -------------------------------------------------
        # SIDE EFFECT FLAGGING
        # -------------------------------------------------
        if side_effects:
            warnings.append("Step has side effects")
            annotations["side_effects"] = True

        # -------------------------------------------------
        # CHAIN LIMIT ENFORCEMENT (optional hard stop)
        # -------------------------------------------------
        chain_len = context.get("chain_length")
        if self.max_chain_length is not None and chain_len is not None:
            if chain_len > self.max_chain_length:
                return ConstraintResult(
                    allowed=False,
                    reason="Chain length limit exceeded",
                )

        # -------------------------------------------------
        # TOOL-SPECIFIC RULE HOOK (future extensibility)
        # -------------------------------------------------
        if tool == "write_file":
            annotations["writes_to_disk"] = True

        if tool == "read_file":
            annotations["reads_from_disk"] = True

        # -------------------------------------------------
        # DEFAULT ALLOW
        # -------------------------------------------------
        return ConstraintResult(
            allowed=True,
            warnings=warnings,
            annotations=annotations,
        )

    # =====================================================
    # CONFIGURATION HELPERS
    # =====================================================

    def block_tool(self, tool_name: str) -> None:
        self.blocked_tools.add(tool_name)

    def unblock_tool(self, tool_name: str) -> None:
        self.blocked_tools.discard(tool_name)

    def block_scope(self, scope: str) -> None:
        self.blocked_scopes.add(scope)

    def set_max_chain_length(self, n: int) -> None:
        self.max_chain_length = n

    # =====================================================
    # DEBUG
    # =====================================================

    def snapshot(self) -> Dict[str, Any]:
        return {
            "blocked_tools": list(self.blocked_tools),
            "blocked_scopes": list(self.blocked_scopes),
            "max_chain_length": self.max_chain_length,
        }