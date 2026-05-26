# core/registries/__init__.py
"""
NextMind v2.0 Registry Layer

Registry-driven component management for transforms, actions, tools, and validation rules.
All components are registered centrally and discovered by capability, not by name.
"""

from core.registries.base import Registry
from core.registries.transform_registry import (
    TransformRegistry,
    TransformSpec,
    TransformInputSchema,
    TransformOutputSchema,
)
from core.registries.action_registry import (
    ActionRegistry,
    ActionSpec,
    Capability,
)
from core.registries.tool_registry import (
    ToolCapabilityRegistry,
    ToolSpec,
    ToolCapability,
    SafetyLevel,
    ToolEffect,
    EffectType,
)
from core.registries.validation_registry import (
    ValidationRuleRegistry,
    ValidationRule,
)

__all__ = [
    "Registry",
    "TransformRegistry",
    "TransformSpec",
    "TransformInputSchema",
    "TransformOutputSchema",
    "ActionRegistry",
    "ActionSpec",
    "Capability",
    "ToolCapabilityRegistry",
    "ToolSpec",
    "ToolCapability",
    "SafetyLevel",
    "ToolEffect",
    "EffectType",
    "ValidationRuleRegistry",
    "ValidationRule",
]