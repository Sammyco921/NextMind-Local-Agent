# core/simple_parser.py
#
# v1.9.1: coarse step extraction only — warnings, not semantic failures.

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from core.artifact_refs import artifact_ref
from core.goal_normalizer import NormalizedGoal, NormalizedStep
from core.planning_types import StructuredStep

_UNKNOWN_TOOL = "unknown"


class SimpleParser:
    """Map normalized pseudo-steps to coarse structured steps (no validation)."""

    def parse_normalized(
        self, normalized: NormalizedGoal
    ) -> Tuple[List[StructuredStep], List[str]]:
        warnings: List[str] = list(normalized.warnings)
        structured: List[StructuredStep] = []

        if not normalized.normalized_steps:
            return [], warnings

        for step in normalized.normalized_steps:
            structured_step, step_warnings = self._map_step(step)
            warnings.extend(step_warnings)
            structured.append(structured_step)

        return structured, warnings

    def parse(self, goal: str) -> Tuple[List[StructuredStep], List[str]]:
        """Legacy entry: caller should prefer parse_normalized via planning pipeline."""
        from core.goal_normalizer import GoalNormalizer

        normalized = GoalNormalizer().normalize(goal)
        return self.parse_normalized(normalized)

    def _map_step(
        self, step: NormalizedStep
    ) -> Tuple[StructuredStep, List[str]]:
        warnings: List[str] = []
        step_id = f"s{step.index}"
        meta: Dict[str, Any] = {
            "raw_nl_step": step.text,
            "goal_step_index": step.index,
            "type_guess": step.type_guess,
        }
        entities = step.entities or {}
        type_guess = step.type_guess

        if type_guess == "create_dir":
            directory = entities.get("directory") or self._first_dir(entities)
            if not directory:
                directory = self._infer_dir_from_paths(entities)
            if not directory:
                warnings.append(f"Step {step.index + 1}: no directory path extracted")
                directory = "workspace"
            filename = f"{directory.rstrip('/')}/.keep"
            return (
                self._structured(
                    step_id,
                    step.index,
                    "ensure_dir",
                    "write_file",
                    {"filename": filename, "content": "."},
                    [],
                    meta,
                    warnings,
                ),
                warnings,
            )

        if type_guess == "write_file" or (
            type_guess == "unknown" and self._looks_like_write(step.text)
        ):
            filename = entities.get("filename") or self._first_file(entities)
            if not filename:
                warnings.append(f"Step {step.index + 1}: no filename extracted")
                filename = "output.txt"
            content = entities.get("content")
            if content is None:
                warnings.append(f"Step {step.index + 1}: no content extracted; using placeholder")
                content = " "
            return (
                self._structured(
                    step_id,
                    step.index,
                    "write",
                    "write_file",
                    {"filename": filename, "content": content},
                    [],
                    meta,
                    warnings,
                ),
                warnings,
            )

        if type_guess == "read_file" or (
            type_guess == "unknown" and "read" in step.text.lower()
        ):
            filename = entities.get("filename") or self._first_file(entities)
            if not filename:
                match = re.search(r"([\w./-]+\.txt)", step.text, re.I)
                filename = match.group(1) if match else "input.txt"
                warnings.append(f"Step {step.index + 1}: inferred read filename '{filename}'")
            return (
                self._structured(
                    step_id,
                    step.index,
                    "read",
                    "read_file",
                    {"filename": filename},
                    [],
                    meta,
                    warnings,
                ),
                warnings,
            )

        if type_guess == "combine":
            output = entities.get("output_file") or self._first_file(entities) or "combo.txt"
            source_files = entities.get("source_files") or entities.get("filenames") or []
            meta["combine_sources"] = source_files
            lower = step.text.lower()
            if "word" in lower and "reverse" in lower:
                meta["combine_mode"] = "combine_reverse_words"
            elif "reverse" in lower or "reversed" in lower:
                meta["combine_mode"] = "combine_reverse"
            else:
                meta["combine_mode"] = "combine"
            return (
                self._structured(
                    step_id,
                    step.index,
                    "combine",
                    "write_file",
                    {
                        "filename": output,
                        "content": {
                            "$transform": meta["combine_mode"],
                            "$sources": [],
                            "$source_files": source_files,
                        },
                    },
                    [],
                    meta,
                    warnings,
                ),
                warnings,
            )

        if type_guess == "list_dir":
            path = entities.get("directory") or self._first_dir(entities) or "."
            return (
                self._structured(
                    step_id,
                    step.index,
                    "list",
                    "list_dir",
                    {"path": path},
                    [],
                    meta,
                    warnings,
                ),
                warnings,
            )

        warnings.append(f"Step {step.index + 1}: unmapped type '{type_guess}' — best-effort list")
        path = entities.get("directory") or "."
        return (
            self._structured(
                step_id,
                step.index,
                "fallback_list",
                "list_dir",
                {"path": path},
                [],
                meta,
                warnings,
            ),
            warnings,
        )

    @staticmethod
    def _structured(
        step_id: str,
        goal_step_index: int,
        action: str,
        tool: str,
        args: dict,
        dependencies: List[str],
        meta: dict,
        warnings: List[str],
    ) -> StructuredStep:
        meta = dict(meta)
        if warnings:
            meta["warnings"] = list(warnings)
        return {
            "id": step_id,
            "action": action,
            "tool": tool,
            "args": args,
            "dependencies": dependencies,
            "metadata": meta,
            "goal_step_index": goal_step_index,
        }

    @staticmethod
    def _looks_like_write(text: str) -> bool:
        lower = text.lower()
        return any(w in lower for w in ("create", "write", "file", "document", "summary"))

    @staticmethod
    def _first_file(entities: dict) -> str | None:
        names = entities.get("filenames") or entities.get("paths") or []
        for p in names:
            if re.search(r"\.\w+$", p):
                return p
        return entities.get("filename")

    @staticmethod
    def _first_dir(entities: dict) -> str | None:
        return entities.get("directory")

    @staticmethod
    def _infer_dir_from_paths(entities: dict) -> str | None:
        for p in entities.get("paths") or []:
            if "/" in p and not re.search(r"\.\w+$", p):
                return p.rstrip("/")
            if "/" in p:
                return p.rsplit("/", 1)[0]
        return None
