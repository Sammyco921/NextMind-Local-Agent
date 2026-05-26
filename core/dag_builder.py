# core/dag_builder.py
#
# v1.9.1 truth layer: dependency inference, graph validation, DAG construction.
#
# INVARIANT: DAGBuilder is a pure function — steps → DAG (no state, no memory).
# No component may depend on previous executions of build().

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from core.artifact_refs import artifact_ref, combine_reverse_sources
from core.artifact_refs import combine_reverse_words_sources
from core.artifact_refs import is_unresolved_value
from core.dag_node import DAG, DAGNode
from core.planning_errors import structured_error_node
from core.planning_types import StructuredStep
from core.types import NodeId, ToolName

_KNOWN_TOOLS = frozenset({"write_file", "read_file", "list_dir"})
_UNKNOWN_TOOL = "unknown"


@dataclass
class DAGBuildResult:
    dag: DAG
    status: str  # "ok" | "error"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    structured_steps: List[StructuredStep] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "ok" and not self.errors


class DAGBuilder:
    """Pure builder: input steps → output DAG. No state, no history, no cross-execution memory."""

    def build(self, steps: List[StructuredStep]) -> DAGBuildResult:
        if not steps:
            return DAGBuildResult(
                dag=DAG(nodes=[structured_error_node("No structured steps", phase="dag_build")]),
                status="error",
                errors=["No structured steps to build DAG"],
            )

        warnings: List[str] = []
        prepared, prep_warnings, prep_errors = self._prepare_steps(steps)
        warnings.extend(prep_warnings)
        if prep_errors:
            return DAGBuildResult(
                dag=DAG(
                    nodes=[
                        structured_error_node(
                            "DAG build failed: " + "; ".join(prep_errors[:5]),
                            phase="dag_build",
                        )
                    ]
                ),
                status="error",
                errors=prep_errors,
                warnings=warnings,
                structured_steps=steps,
            )

        with_deps, dep_warnings = self._infer_dependencies(prepared)
        warnings.extend(dep_warnings)

        nodes, id_map, build_errors = self._construct_nodes(with_deps)
        if build_errors:
            return DAGBuildResult(
                dag=DAG(
                    nodes=[
                        structured_error_node(
                            "DAG build failed: " + "; ".join(build_errors[:5]),
                            phase="dag_build",
                        )
                    ]
                ),
                status="error",
                errors=build_errors,
                warnings=warnings,
                structured_steps=with_deps,
            )

        nodes = self._remap_nodes_artifact_refs(nodes, id_map)
        struct_errors = self._validate_dependency_graph(nodes)
        if struct_errors:
            return DAGBuildResult(
                dag=DAG(
                    nodes=[
                        structured_error_node(
                            "DAG structure invalid: " + "; ".join(struct_errors[:5]),
                            phase="dag_build",
                        )
                    ]
                ),
                status="error",
                errors=struct_errors,
                warnings=warnings,
                structured_steps=with_deps,
            )

        return DAGBuildResult(
            dag=DAG(nodes=nodes),
            status="ok",
            errors=[],
            warnings=warnings,
            structured_steps=with_deps,
        )

    def _prepare_steps(
        self, steps: List[StructuredStep]
    ) -> Tuple[List[StructuredStep], List[str], List[str]]:
        warnings: List[str] = []
        errors: List[str] = []
        out: List[StructuredStep] = []
        for step in steps:
            tool = step.get("tool") or _UNKNOWN_TOOL
            if tool == _UNKNOWN_TOOL:
                errors.append(
                    f"Step {step.get('id')}: unknown tool — DAG build failed"
                )
                continue
            if tool not in _KNOWN_TOOLS:
                errors.append(f"Step {step.get('id')}: unsupported tool '{tool}'")
                continue
            out.append(dict(step))
        return out, warnings, errors

    def _infer_dependencies(
        self, steps: List[StructuredStep]
    ) -> Tuple[List[StructuredStep], List[str]]:
        warnings: List[str] = []
        file_to_writer: Dict[str, str] = {}
        read_by_file: Dict[str, str] = {}
        all_reads: List[str] = []
        result: List[StructuredStep] = []

        for step in steps:
            step = dict(step)
            tool = step.get("tool", "")
            args = dict(step.get("args") or {})
            meta = dict(step.get("metadata") or {})
            step_id = step["id"]
            deps: List[str] = list(step.get("dependencies") or [])

            if tool == "write_file" and "filename" in args:
                fn = str(args["filename"])
                content = args.get("content")
                if isinstance(content, dict) and "$transform" in content:
                    step, deps, w = self._wire_transform(
                        step, step_id, content, meta, all_reads, read_by_file
                    )
                    warnings.extend(w)
                    args = step["args"]
                file_to_writer[fn] = step_id
                if fn.split("/")[-1] != fn:
                    file_to_writer[fn.split("/")[-1]] = step_id

            elif tool == "read_file":
                fn = str(args.get("filename", ""))
                basename = fn.split("/")[-1]
                if fn in file_to_writer:
                    deps = sorted(set(deps + [file_to_writer[fn]]))
                elif basename in file_to_writer:
                    deps = sorted(set(deps + [file_to_writer[basename]]))
                else:
                    warnings.append(
                        f"Step {step_id}: read '{fn}' has no prior write in plan "
                        "(assuming external file)"
                    )
                read_by_file[fn] = step_id
                read_by_file[basename] = step_id
                all_reads.append(step_id)

            elif tool == "list_dir":
                if all_reads:
                    deps = sorted(set(deps + [all_reads[-1]]))
                elif result:
                    deps = sorted(set(deps + [result[-1]["id"]]))

            step["dependencies"] = deps
            step["args"] = args
            step["metadata"] = meta
            result.append(step)

        return result, warnings

    def _wire_transform(
        self,
        step: StructuredStep,
        step_id: str,
        content: dict,
        meta: dict,
        all_reads: List[str],
        read_by_file: Dict[str, str],
    ) -> Tuple[StructuredStep, List[str], List[str]]:
        warnings: List[str] = []
        transform = content.get("$transform", "combine")
        source_files = content.get("$source_files") or meta.get("combine_sources") or []

        read_ids: List[str] = []
        for sf in source_files:
            base = sf.split("/")[-1]
            if sf in read_by_file:
                read_ids.append(read_by_file[sf])
            elif base in read_by_file:
                read_ids.append(read_by_file[base])
            else:
                warnings.append(
                    f"Step {step_id}: combine source '{sf}' has no matching read in plan"
                )

        if not read_ids:
            read_ids = list(all_reads)

        if not read_ids:
            warnings.append(f"Step {step_id}: combine has no read dependencies")
            return step, [], warnings

        mode = str(meta.get("combine_mode", ""))
        if transform == "combine_reverse_words" or mode == "combine_reverse_words":
            new_content = combine_reverse_words_sources(read_ids)
        elif (
            transform in ("combine_reverse", "combine")
            and ("reverse" in mode or transform == "combine_reverse")
        ):
            new_content = combine_reverse_sources(read_ids)
        elif transform == "combine" or mode == "combine":
            new_content = {
                "$transform": "combine",
                "$sources": [artifact_ref(rid) for rid in read_ids],
            }
        else:
            new_content = {
                "$transform": "combine",
                "$sources": [artifact_ref(rid) for rid in read_ids],
            }

        args = dict(step.get("args") or {})
        args["content"] = new_content
        step["args"] = args
        return step, sorted(set(read_ids)), warnings

    def _construct_nodes(
        self, steps: List[StructuredStep]
    ) -> Tuple[List[DAGNode], Dict[str, NodeId], List[str]]:
        errors: List[str] = []
        nodes: List[DAGNode] = []
        id_map: Dict[str, NodeId] = {}

        for step in steps:
            step_id = step["id"]
            tool = step.get("tool", "")
            raw_args = step.get("args")
            struct_deps = list(step.get("dependencies") or [])

            if raw_args is None:
                errors.append(f"Step {step_id}: missing args")
                continue

            if self._has_null_values(raw_args):
                errors.append(f"Step {step_id}: args contain null values")
                continue

            if self._has_empty_literal_strings(raw_args):
                errors.append(f"Step {step_id}: empty literal argument")
                continue

            unresolved = [d for d in struct_deps if d not in id_map]
            if unresolved:
                errors.append(f"Step {step_id}: unresolved dependencies {unresolved}")
                continue

            node_id: NodeId = f"n{len(nodes)}"
            dag_deps = sorted({id_map[d] for d in struct_deps})

            step_meta = step.get("metadata") or {}
            nodes.append(
                DAGNode(
                    node_id=node_id,
                    tool_name=tool,  # type: ignore[assignment]
                    raw_args=dict(raw_args),
                    dependencies=dag_deps,
                    metadata={
                        "structured_step_id": step_id,
                        "action": step.get("action", ""),
                        "goal_step_index": step.get("goal_step_index", len(nodes)),
                        "raw_nl_step": step_meta.get("raw_nl_step", ""),
                    },
                )
            )
            id_map[step_id] = node_id

        return nodes, id_map, errors

    @staticmethod
    def _validate_dependency_graph(nodes: List[DAGNode]) -> List[str]:
        errors: List[str] = []
        valid_ids = {n.node_id for n in nodes}

        for node in nodes:
            for dep in node.dependencies:
                if dep not in valid_ids:
                    errors.append(
                        f"Node {node.node_id} depends on unknown step '{dep}'"
                    )

        if not nodes:
            return errors

        children: Dict[str, List[str]] = {n.node_id: [] for n in nodes}
        for node in nodes:
            for dep in node.dependencies:
                children.setdefault(dep, []).append(node.node_id)

        roots = [n.node_id for n in nodes if not n.dependencies]
        reachable: Set[str] = set()
        queue = list(roots)
        while queue:
            cur = queue.pop(0)
            if cur in reachable:
                continue
            reachable.add(cur)
            queue.extend(children.get(cur, []))

        for node in nodes:
            if node.node_id not in reachable:
                errors.append(f"Orphan node (not reachable from roots): {node.node_id}")

        in_degree = {n.node_id: len(n.dependencies) for n in nodes}
        order: List[str] = []
        queue = sorted(nid for nid, d in in_degree.items() if d == 0)
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for child in children.get(nid, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(nodes):
            errors.append("Circular dependency detected in DAG")

        return errors

    @classmethod
    def _remap_nodes_artifact_refs(
        cls, nodes: List[DAGNode], id_map: Dict[str, NodeId]
    ) -> List[DAGNode]:
        return [
            DAGNode(
                node_id=n.node_id,
                tool_name=n.tool_name,
                raw_args=cls._remap_ref_values(n.raw_args, id_map),
                dependencies=n.dependencies,
                metadata=n.metadata,
            )
            for n in nodes
        ]

    @classmethod
    def _remap_ref_values(cls, value: Any, id_map: Dict[str, NodeId]) -> Any:
        if isinstance(value, dict):
            out = {
                k: cls._remap_ref_values(v, id_map)
                for k, v in value.items()
                if k != "$source_files"
            }
            if "$artifact" in out and isinstance(out["$artifact"], str):
                sid = out["$artifact"]
                if sid in id_map:
                    out["$artifact"] = id_map[sid]
            return out
        if isinstance(value, list):
            return [cls._remap_ref_values(v, id_map) for v in value]
        return value

    @staticmethod
    def _has_null_values(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, dict):
            return any(DAGBuilder._has_null_values(v) for v in value.values())
        if isinstance(value, list):
            return any(DAGBuilder._has_null_values(v) for v in value)
        return False

    @staticmethod
    def _has_empty_literal_strings(args: Dict[str, Any]) -> bool:
        for value in args.values():
            if is_unresolved_value(value):
                continue
            if isinstance(value, str) and value.strip() == "":
                return True
        return False
