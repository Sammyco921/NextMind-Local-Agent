# core/transform_semantics.py
#
# Pure semantic rules for transform verification (evaluator + repair).
#
# ARCHITECTURAL PRINCIPLE:
# GoalConstraints is a STRUCTURED SPEC provided by the planning layer.
# It is NOT derived from natural language or DAG heuristics.
# Semantic evaluation only validates ExecutionTrace against this spec.
# If constraints are missing/empty, evaluation MUST PASS (no assumptions).

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GoalConstraints:
    """
    Structured output specification from the planning layer.
    
    This is the ONLY source of truth for semantic evaluation.
    Constraints are explicitly set by the planner based on the
    structured intent, NOT derived from natural language or DAG heuristics.
    
    If a constraint is not explicitly set, semantic evaluation
    MUST NOT assume it is required (defaults to False).
    """

    requires_two_file_reads: bool = False
    requires_combine: bool = False
    requires_word_reverse: bool = False
    requires_char_reverse: bool = False
    requires_output_file: bool = False
    combine_separator: str = ""
    output_filename_hint: Optional[str] = None
    raw_goal: str = ""

    @classmethod
    def empty(cls, raw_goal: str = "") -> "GoalConstraints":
        """
        Create empty constraints - no requirements assumed.
        
        This is the safe default when no explicit output_spec is provided.
        Semantic evaluation with empty constraints MUST PASS.
        """
        return cls(raw_goal=raw_goal)

    @classmethod
    def from_goal(cls, goal: str) -> "GoalConstraints":
        """
        Create empty constraints from a goal string.
        
        This is a compatibility shim for the (currently dormant) RepairPlanner path.
        Planning layer provides structured constraints explicitly; this method
        returns safe defaults when no constraints have been provided.
        """
        return cls(raw_goal=goal)


def combine_parts(parts: List[str], separator: str = "") -> str:
    return separator.join(parts)


def char_reverse(text: str) -> str:
    return text[::-1]


def word_reverse(text: str) -> str:
    words = text.split()
    return " ".join(reversed(words))


def combine_then_char_reverse(parts: List[str], separator: str = "") -> str:
    return char_reverse(combine_parts(parts, separator))


def combine_then_word_reverse(parts: List[str], separator: str = " ") -> str:
    return word_reverse(combine_parts(parts, separator))


def is_char_level_reverse_of(parts: List[str], output: str, separator: str = "") -> bool:
    return output == combine_then_char_reverse(parts, separator)


def is_word_level_reverse_of(parts: List[str], output: str, separator: str = " ") -> bool:
    return output == combine_then_word_reverse(parts, separator)
