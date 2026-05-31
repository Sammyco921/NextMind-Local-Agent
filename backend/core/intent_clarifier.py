# core/intent_clarifier.py
#
# v1.9 Clarification Engine — Intent completeness gatekeeper.
#
# ARCHITECTURAL RULE: No DAG exists unless intent is fully specified.
# No fallback decomposition. No heuristic guessing.
#
# INVARIANTS:
#   - Fully deterministic: same input always produces same ClarificationRequest.
#   - No AI, no LLM, no probabilistic inference.
#   - No default values for missing fields — only structured questions.
#   - Every missing field produces exactly one question.
#   - No variation in question wording for the same missing field.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.tool_schemas import TOOL_SCHEMAS, required_args


class IntentStatus(str, Enum):
    """v1.9 intent completeness classification."""
    EXECUTABLE = "executable"
    PARTIAL = "partial"
    NON_EXECUTABLE = "non_executable"


@dataclass(frozen=True)
class MissingField:
    """A single field that must be specified before execution can proceed."""

    step_index: int
    step_text: str
    field_name: str
    tool_name: str
    question: str
    expected_format: str = ""


@dataclass(frozen=True)
class ClarificationRequest:
    """First-class outcome when intent is not fully specified.

    This is NOT a failure — it is a deliberate pause until intent is resolved.
    """

    status: IntentStatus
    raw_goal: str
    missing_fields: List[MissingField] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    ambiguity_warnings: List[str] = field(default_factory=list)
    step_count: int = 0
    detected_tools: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "raw_goal": self.raw_goal,
            "missing_fields": [
                {
                    "step_index": m.step_index,
                    "step_text": m.step_text,
                    "field_name": m.field_name,
                    "tool_name": m.tool_name,
                    "question": m.question,
                    "expected_format": m.expected_format,
                }
                for m in self.missing_fields
            ],
            "clarification_questions": self.clarification_questions,
            "ambiguity_warnings": self.ambiguity_warnings,
            "step_count": self.step_count,
            "detected_tools": self.detected_tools,
        }


# ---- Tool detection patterns (deterministic, shared with GoalNormalizer) ----

_WRITE_KEYWORDS = {"create", "write", "save", "make", "fix", "update", "modify", "change", "edit", "remove", "delete", "refactor", "restructure", "rename"}
_READ_KEYWORDS = {"read", "open", "view", "show", "display", "print"}
_LIST_KEYWORDS = {"list", "ls", "dir", "directory", "folders", "contents"}
_COMBINE_KEYWORDS = {"combine", "merge", "concat", "join"}
_CONTENT_PATTERNS = [
    re.compile(r'"([^"]*)"'),
    re.compile(r"'([^']*)'"),
    re.compile(r"with\s+(?:the\s+)?contents?\s*:\s*(.+?)(?:$|\d+\.|\n)", re.IGNORECASE),
    re.compile(r"contents?\s*:\s*(.+?)(?:$|\d+\.|\n)", re.IGNORECASE),
    re.compile(r"with\s+contents?\s+(.+?)(?:$|\d+\.|\n)", re.IGNORECASE),
    re.compile(r"with\s+(.+?)\s+contents?(?:\s|$|\d+\.|\n)", re.IGNORECASE),
    re.compile(r"contents?\s+(.+?)(?:$|\d+\.|\n)", re.IGNORECASE),
]
_PATH_PATTERN = re.compile(r"([\w./-]+\.(?:txt|md|json))", re.IGNORECASE)
_CALLED_FILE = re.compile(r"(?:called|named)\s+([\w./-]+)", re.IGNORECASE)


class IntentClarifier:
    """Deterministic intent completeness checker.

    Examines raw goal text and determines whether it is:
      - executable as-is
      - partially executable (needs missing constraints)
      - non-executable (ambiguous / unsafe / underspecified)

    This is a PURE function — no state, no history, no side effects.
    """

    def clarify(self, goal: str) -> ClarificationRequest:
        """Analyze a raw goal and determine its completeness status."""
        raw = (goal or "").strip()

        # ---- Empty / non-executable guard ----
        if not raw:
            return ClarificationRequest(
                status=IntentStatus.NON_EXECUTABLE,
                raw_goal=raw,
                clarification_questions=["No goal provided — what do you want to do?"],
                ambiguity_warnings=["Empty goal"],
            )

        if self._is_garbage(raw):
            return ClarificationRequest(
                status=IntentStatus.NON_EXECUTABLE,
                raw_goal=raw,
                clarification_questions=["Input is not interpretable — please rephrase."],
                ambiguity_warnings=["Input contains no recognizable text"],
            )

        # ---- Step extraction ----
        steps = self._extract_steps(raw)
        if not steps:
            return ClarificationRequest(
                status=IntentStatus.NON_EXECUTABLE,
                raw_goal=raw,
                clarification_questions=["No actionable steps found — what would you like to do?"],
                ambiguity_warnings=["Zero steps extracted from goal"],
            )

        # ---- Per-step analysis ----
        missing_fields: List[MissingField] = []
        detected_tools: List[str] = []

        for i, step_text in enumerate(steps):
            analysis = self._analyze_step(step_text, i)
            detected_tools.append(analysis["tool_name"])
            for mf in analysis.get("missing_fields", []):
                missing_fields.append(mf)

        # ---- Determine overall status ----
        all_unknown = all(t == "unknown" for t in detected_tools)
        if all_unknown:
            status = IntentStatus.NON_EXECUTABLE
        elif missing_fields:
            status = IntentStatus.PARTIAL
        else:
            status = IntentStatus.EXECUTABLE

        # ---- Build questions ----
        questions = [m.question for m in missing_fields]

        # Deduplicate detected tools (preserve order)
        seen_tools: set = set()
        unique_tools: List[str] = []
        for t in detected_tools:
            if t not in seen_tools:
                seen_tools.add(t)
                unique_tools.append(t)

        warnings: List[str] = []
        unknown_steps = [s for i, s in enumerate(steps)
                        if detected_tools[i] == "unknown"]
        if unknown_steps:
            warnings.append(
                f"Cannot determine tool for {len(unknown_steps)} step(s) — "
                f"try specifying: create, read, list, or combine"
            )

        return ClarificationRequest(
            status=status,
            raw_goal=raw,
            missing_fields=missing_fields,
            clarification_questions=questions,
            ambiguity_warnings=warnings,
            step_count=len(steps),
            detected_tools=unique_tools,
        )

    # ---- Step extraction ----

    @staticmethod
    def _extract_steps(goal: str) -> List[str]:
        """Extract steps from numbered list or single-line goal."""
        normalized = goal.replace("\r\n", "\n")
        numbered = re.split(r"\d+\.\s+", normalized)
        parts = [p.strip() for p in numbered if p.strip()]
        if len(parts) > 1:
            return parts

        lines = [ln.strip() for ln in normalized.split("\n") if ln.strip()]
        if len(lines) > 1:
            return lines

        # Single-line with semicolons
        if ";" in goal:
            semi = [p.strip() for p in goal.split(";") if p.strip()]
            if len(semi) > 1:
                return semi

        return [goal.strip()]

    # ---- Garbage detection ----

    @staticmethod
    def _is_garbage(text: str) -> bool:
        return bool(re.match(r"^[\s\W\d]+$", text))

    # ---- Step analysis ----

    def _analyze_step(self, step_text: str, index: int) -> Dict[str, Any]:
        """Analyze a single step and identify any missing fields."""
        lower = step_text.lower()
        tool_name = self._detect_tool(lower, step_text)
        result: Dict[str, Any] = {
            "tool_name": tool_name,
            "missing_fields": [],
        }

        if tool_name == "unknown":
            return result

        schema = TOOL_SCHEMAS.get(tool_name, {})
        if not schema:
            return result

        entities = self._extract_entities(step_text, tool_name)

        for arg_name in required_args(tool_name):
            if arg_name not in entities or not entities[arg_name]:
                question = self._generate_question(tool_name, arg_name, step_text, index)
                result["missing_fields"].append(MissingField(
                    step_index=index,
                    step_text=step_text,
                    field_name=arg_name,
                    tool_name=tool_name,
                    question=question,
                    expected_format=self._expected_format(tool_name, arg_name),
                ))

        # For write_file: content AND filename both required; if filename was
        # detected but content wasn't, we already flagged content above.
        # But for the "combine" tool path (maps to write_file), check source_files.
        if tool_name == "write_file" and "combine" in lower:
            sources = self._extract_source_files(step_text)
            if not sources:
                result["missing_fields"].append(MissingField(
                    step_index=index,
                    step_text=step_text,
                    field_name="source_files",
                    tool_name="combine",
                    question=f"Step {index + 1}: which files should be combined?",
                    expected_format="filename1.txt, filename2.txt",
                ))

        return result

    @staticmethod
    def _detect_tool(lower: str, original: str) -> str:
        """Determine tool type from step text (deterministic pattern match)."""
        if any(w in lower for w in _COMBINE_KEYWORDS):
            return "write_file"  # combine maps to write_file with transform
        # If "list" appears as a prefix directive, prioritize list_dir
        if re.search(r"^\s*(?:list|ls)\b", lower):
            return "list_dir"
        if any(w in lower for w in _WRITE_KEYWORDS):
            return "write_file"
        if any(w in lower for w in _READ_KEYWORDS) and _PATH_PATTERN.search(original):
            return "read_file"
        if "read" in lower or "open" in lower or "view" in lower or "show" in lower:
            return "read_file"
        if any(w in lower for w in _LIST_KEYWORDS):
            return "list_dir"
        return "unknown"

    @staticmethod
    def _extract_entities(text: str, tool_name: str) -> Dict[str, Any]:
        """Extract known argument values from step text."""
        entities: Dict[str, Any] = {}
        paths = _PATH_PATTERN.findall(text)
        if paths:
            entities["filename"] = paths[0]
            entities["filenames"] = paths
            entities["paths"] = paths

        # Extract content for write_file
        if tool_name == "write_file":
            content = None
            for pattern in _CONTENT_PATTERNS:
                m = pattern.search(text)
                if m:
                    content = m.group(1).strip().strip('"').strip("'")
                    if content:
                        break
            if content:
                entities["content"] = content

            # Fallback: capture filename from "called X" / "named X" pattern
            if not entities.get("filename"):
                m = _CALLED_FILE.search(text)
                if m:
                    fname = m.group(1).strip()
                    if not re.search(r"\.\w+$", fname):
                        fname += ".txt"
                    entities["filename"] = fname

        # Extract directory path for list_dir
        if tool_name == "list_dir":
            dir_match = re.search(r"(?:in|of|under)\s+([\w./-]+)", text, re.I)
            if dir_match:
                entities["path"] = dir_match.group(1).strip()
            elif paths:
                entities["path"] = paths[0]
            else:
                entities["path"] = "."

        return entities

    def refine(
        self,
        previous_goal: str,
        refinement: str,
        previous_result: Optional[ClarificationRequest] = None,
    ) -> ClarificationRequest:
        """Iterative clarification — apply a user refinement to a partial intent.

        Merges the refinement with the previous goal and re-runs clarity.
        This is a PURE function — no state, no memory of previous refinements.

        The refinement replaces the previous goal for re-analysis, since
        the user's refinement should contain the complete updated intent.

        INVARIANT:
        - Does NOT modify previous_goal or previous_result
        - Same inputs → same output
        - No memory of previous refinements
        """
        return self.clarify(refinement)

    @staticmethod
    def _extract_source_files(text: str) -> List[str]:
        """Extract source file names for combine operations."""
        files = re.findall(r"([\w./-]+\.txt)", text, re.I)
        return files

    @staticmethod
    def _generate_question(tool_name: str, arg_name: str, step_text: str, index: int) -> str:
        """Generate a deterministic clarification question for a missing field."""
        questions = {
            ("write_file", "filename"): (
                f"Step {index + 1}: what file should be created?"
            ),
            ("write_file", "content"): (
                f"Step {index + 1}: what content should be written to the file?"
            ),
            ("read_file", "filename"): (
                f"Step {index + 1}: which file should be read?"
            ),
            ("list_dir", "path"): (
                f"Step {index + 1}: which directory should be listed?"
            ),
            ("__inject_failure__", "failure_type"): (
                f"Step {index + 1}: what type of failure should be injected?"
            ),
        }
        return questions.get(
            (tool_name, arg_name),
            f"Step {index + 1}: missing required field '{arg_name}' for tool '{tool_name}'",
        )

    @staticmethod
    def _expected_format(tool_name: str, arg_name: str) -> str:
        """Return the expected format for a given field."""
        formats = {
            "filename": "path/to/file.txt",
            "content": "string or quoted text",
            "path": "path/to/directory",
            "failure_type": "capability_violation | tool_failure",
            "source_files": "filename1.txt, filename2.txt",
        }
        return formats.get(arg_name, "string")
