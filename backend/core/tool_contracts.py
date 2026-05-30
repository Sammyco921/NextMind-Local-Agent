# core/tool_contracts.py
#
# v1.4 formal tool contracts — every tool MUST declare input/output types.
# Immutable after registration.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from core.artifact_types import ArtifactType


@dataclass(frozen=True)
class ToolContract:
    """Formal contract for a single tool — input types, output type, guarantees."""

    name: str
    input_types: Dict[str, ArtifactType]  # arg_name → expected input artifact type
    output_type: ArtifactType             # produced artifact type
    deterministic: bool = True
    side_effects: List[str] = field(default_factory=list)  # e.g. ["filesystem_write"]



# ============================================================
# CANONICAL TOOL CONTRACTS (single source of truth)
# ============================================================
# Every tool used in the system must have a contract here.

INJECT_FAILURE_TOOL = "__inject_failure__"

_TOOL_CONTRACTS: Dict[str, ToolContract] = {
    "write_file": ToolContract(
        name="write_file",
        input_types={"filename": ArtifactType.TEXT, "content": ArtifactType.TEXT},
        output_type=ArtifactType.FILE,
        deterministic=True,
        side_effects=["filesystem_write"],
    ),
    "read_file": ToolContract(
        name="read_file",
        input_types={"filename": ArtifactType.TEXT},
        output_type=ArtifactType.TEXT,
        deterministic=True,
        side_effects=["filesystem_read"],
    ),
    "list_dir": ToolContract(
        name="list_dir",
        input_types={"path": ArtifactType.TEXT},
        output_type=ArtifactType.DIRECTORY,
        deterministic=True,
        side_effects=["filesystem_read"],
    ),
    "text_to_json": ToolContract(
        name="text_to_json",
        input_types={"text": ArtifactType.TEXT},
        output_type=ArtifactType.JSON,
        deterministic=True,
        side_effects=[],
    ),
    "json_to_text": ToolContract(
        name="json_to_text",
        input_types={"json_data": ArtifactType.JSON},
        output_type=ArtifactType.TEXT,
        deterministic=True,
        side_effects=[],
    ),
    INJECT_FAILURE_TOOL: ToolContract(
        name=INJECT_FAILURE_TOOL,
        input_types={},
        output_type=ArtifactType.NULL,
        deterministic=True,
        side_effects=[],
    ),
    "file_to_text": ToolContract(
        name="file_to_text",
        input_types={"file_data": ArtifactType.FILE},
        output_type=ArtifactType.TEXT,
        deterministic=True,
        side_effects=[],
    ),
}


def get_contract(name: str) -> ToolContract:
    if name not in _TOOL_CONTRACTS:
        raise ValueError(f"Unknown tool contract: {name}")
    return _TOOL_CONTRACTS[name]


def has_contract(name: str) -> bool:
    return name in _TOOL_CONTRACTS


def register_contract(contract: ToolContract) -> None:
    if contract.name in _TOOL_CONTRACTS:
        raise ValueError(f"Contract already registered: {contract.name}")
    _TOOL_CONTRACTS[contract.name] = contract


def known_contracts() -> Set[str]:
    return set(_TOOL_CONTRACTS.keys())



