# core/registries/validation_registry.py
"""
Registry for validation rules used in pre-execution and post-execution validation.

Validation rules are applied to plans and execution results to ensure
correctness and constraint satisfaction.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from core.registries.base import Registry


class ValidationCategory(Enum):
    """Categories for validation rules."""
    STRUCTURAL = "structural"  # DAG structure problems
    EXECUTION = "execution"    # Execution failures
    SEMANTIC = "semantic"      # Semantic correctness
    TRANSFORM = "transform"    # Transform correctness
    CONSTRAINT = "constraint"  # Constraint violations
    TRACE = "trace"           # Trace fidelity
    DEPENDENCY = "dependency"  # Dependency issues


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    FATAL = "fatal"           # Cannot recover
    ERROR = "error"           # Must fix to pass
    WARNING = "warning"       # Non-blocking
    INFO = "info"             # Informational


@dataclass(frozen=True)
class ValidationRule:
    """
    A validation rule that can be applied to plans or execution.
    
    Rules are functions that take a context and return a list of issues.
    """
    rule_id: str
    display_name: str
    description: str
    category: ValidationCategory
    default_severity: ValidationSeverity
    validator: Callable[..., List[Dict[str, Any]]]  # Validation function
    applies_to: List[str] = field(default_factory=list)  # Plan/execution phases
    version: str = "1.0.0"


class ValidationRuleRegistry(Registry[ValidationRule]):
    """
    Registry for validation rules.
    
    Rules are applied during validation phases to check plan and
    execution correctness.
    """

    def __init__(self):
        self._rules: Dict[str, ValidationRule] = {}

    def register(
        self, rule: ValidationRule, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"Rule already registered: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> ValidationRule:
        if rule_id not in self._rules:
            raise KeyError(f"Unknown validation rule: {rule_id}")
        return self._rules[rule_id]

    def has(self, rule_id: str) -> bool:
        return rule_id in self._rules

    def keys(self) -> List[str]:
        return sorted(self._rules.keys())

    def validate(self, rule_id: str, context: Dict[str, Any]) -> List[str]:
        """Validate that a rule exists (not the rule's validation logic)."""
        if rule_id not in self._rules:
            return [f"Unknown validation rule: {rule_id}"]
        return []

    def get_metadata(self, key: str) -> Dict[str, Any]:
        rule = self._rules.get(key)
        if rule:
            return {
                "display_name": rule.display_name,
                "description": rule.description,
                "category": rule.category.value,
                "severity": rule.default_severity.value,
            }
        return {}

    def execute(self, rule_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a validation rule.
        
        Args:
            rule_id: The rule to execute
            context: Context for validation
            
        Returns:
            List of issue dictionaries (empty if valid)
        """
        rule = self.get(rule_id)
        return rule.validator(context)

    def get_rules_for_phase(self, phase: str) -> List[ValidationRule]:
        """
        Get all rules that apply to a specific phase.
        
        Args:
            phase: The phase to get rules for
            
        Returns:
            List of applicable validation rules
        """
        return [
            rule for rule in self._rules.values()
            if phase in rule.applies_to
        ]

    def get_rules_for_category(self, category: ValidationCategory) -> List[ValidationRule]:
        """
        Get all rules in a specific category.
        
        Args:
            category: The category to get rules for
            
        Returns:
            List of validation rules in the category
        """
        return [
            rule for rule in self._rules.values()
            if rule.category == category
        ]