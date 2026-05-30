# core/execution_spec.py
#
# v1.8: ExecutionSpec — versioned, identity-locked execution contract.
#
# ARCHITECTURAL RULE: Every module reads mode-specific behavior from
# ExecutionSpec. Zero `if mode == ...` branches outside this file.
#
# INVARIANTS:
#   - ExecutionSpec is immutable (frozen dataclass).
#   - Same (mode + version) always produces identical spec_id and spec_hash.
#   - No randomness, no heuristics, no AI.
#   - Factory for_mode() is the only way to create a spec.
#   - spec_hash is a stable cryptographic digest of all behavioral fields.
#   - Any behavioral change → different spec_hash → hard failure on mismatch.

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from core.execution_mode import ExecutionMode


SPEC_VERSION = "1.8.0"
FAILURE_INJECTION_TOOL = "__inject_failure__"

_STRESS_SCALE_FACTOR = 0.5
_BASE_ALLOWED_TOOLS = frozenset({"write_file", "read_file", "list_dir"})
_FAILURE_ALLOWED_TOOLS = frozenset({"write_file", "read_file", "list_dir", FAILURE_INJECTION_TOOL})


@dataclass(frozen=True)
class ExecutionSpec:
    """Immutable, deterministic, identity-locked specification for DAG execution.

    This is the SINGLE source of truth for all mode-specific rules.
    No module other than execution_spec.py contains mode-branching logic.

    spec_id:   Deterministic human-readable identifier (mode + version).
    version:   Semantic version string.
    spec_hash: SHA-256 digest of all behavioral fields — any behavioral
               change produces a different hash, triggering hard failure.
    """

    mode: ExecutionMode

    # Tool policy — supersedes hardcoded _KNOWN_TOOLS in DAGBuilder
    allowed_tools: FrozenSet[str]

    # Identity
    spec_id: str = ""
    version: str = SPEC_VERSION
    spec_hash: str = ""

    # Mode flags
    expand_dag: bool = False
    inject_failure: bool = False
    requires_failure_node: bool = False

    # Stress expansion parameter
    stress_scale_factor: float = _STRESS_SCALE_FACTOR

    # Failure injection
    failure_tool: str = FAILURE_INJECTION_TOOL

    def __post_init__(self) -> None:
        """Auto-compute identity fields if not explicitly provided."""
        if not self.spec_id:
            computed_id = f"spec.{self.mode.value}.{self.version}"
            object.__setattr__(self, "spec_id", computed_id)
        if not self.spec_hash:
            canonical = self._build_canonical_dict()
            raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            object.__setattr__(self, "spec_hash", h)

    # ---- Canonical serialization ----

    def _build_canonical_dict(self) -> Dict[str, Any]:
        """Build a canonical dict of ALL behavioral fields (no runtime state)."""
        return {
            "version": self.version,
            "mode": self.mode.value,
            "allowed_tools": sorted(self.allowed_tools),
            "expand_dag": self.expand_dag,
            "inject_failure": self.inject_failure,
            "requires_failure_node": self.requires_failure_node,
            "stress_scale_factor": self.stress_scale_factor,
            "failure_tool": self.failure_tool,
        }

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Deterministic dict of all behavior-defining fields."""
        return self._build_canonical_dict()

    def to_canonical_json(self) -> str:
        """Deterministic JSON representation (sorted keys, no extra whitespace)."""
        return json.dumps(
            self._build_canonical_dict(),
            sort_keys=True,
            ensure_ascii=False,
        )

    # ---- Computed helpers ----

    def compute_synthetic_node_count(self, base_count: int) -> int:
        """Deterministic: how many synthetic nodes to add for this spec."""
        if self.expand_dag:
            extra = int(base_count * self.stress_scale_factor)
            return max(1, extra)
        if self.inject_failure or self.requires_failure_node:
            return 1
        return 0

    @staticmethod
    def compute_failure_insertion_index(node_count: int) -> int:
        """Deterministic: where to insert the failure node (floor(n/2))."""
        return max(0, node_count // 2)

    def tool_is_allowed(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools

    # ---- Factory ----

    @staticmethod
    def for_mode(mode: ExecutionMode) -> ExecutionSpec:
        spec_id = f"spec.{mode.value}.{SPEC_VERSION}"
        if mode == ExecutionMode.NORMAL:
            return ExecutionSpec(
                mode=mode,
                spec_id=spec_id,
                allowed_tools=_BASE_ALLOWED_TOOLS,
            )
        if mode == ExecutionMode.STRESS_TEST:
            return ExecutionSpec(
                mode=mode,
                spec_id=spec_id,
                allowed_tools=_BASE_ALLOWED_TOOLS,
                expand_dag=True,
            )
        if mode == ExecutionMode.FAILURE_INJECTION:
            return ExecutionSpec(
                mode=mode,
                spec_id=spec_id,
                allowed_tools=_FAILURE_ALLOWED_TOOLS,
                inject_failure=True,
                requires_failure_node=True,
            )
        raise ValueError(f"Unknown execution mode: {mode}")

    # ---- Hash utilities ----

    @staticmethod
    def compute_spec_hash(canonical_dict: Dict[str, Any]) -> str:
        """Static utility: compute spec_hash from a canonical dict."""
        raw = json.dumps(canonical_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
