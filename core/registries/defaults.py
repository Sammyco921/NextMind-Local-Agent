# core/registries/defaults.py
"""
Default registrations for NextMind v2.0 registries.

These are the built-in transforms, actions, and tools that come with NextMind.
"""

from typing import Dict, Any
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
    ValidationCategory,
    ValidationSeverity,
)


def register_default_transforms(registry: TransformRegistry) -> None:
    """Register all built-in transforms."""

    # combine: Concatenate inputs
    registry.register(TransformSpec(
        transform_id="combine",
        display_name="Combine",
        description="Concatenate multiple string inputs",
        input_schema=[
            TransformInputSchema("inputs", "list[string]", required=True, description="Inputs to combine"),
        ],
        output_schema=TransformOutputSchema("string", "Combined string"),
        resolver=lambda inputs: "".join(str(i) for i in inputs),
        deterministic=True,
    ))

    # combine_reverse: Concatenate and reverse (character-level)
    registry.register(TransformSpec(
        transform_id="combine_reverse",
        display_name="Combine and Reverse",
        description="Concatenate inputs and reverse the result (character-level)",
        input_schema=[
            TransformInputSchema("inputs", "list[string]", required=True),
        ],
        output_schema=TransformOutputSchema("string", "Reversed combined string"),
        resolver=lambda inputs: "".join(str(i) for i in inputs)[::-1],
        deterministic=True,
    ))

    # combine_reverse_words: Concatenate and reverse word order
    registry.register(TransformSpec(
        transform_id="combine_reverse_words",
        display_name="Combine and Reverse Words",
        description="Concatenate inputs and reverse word order",
        input_schema=[
            TransformInputSchema("inputs", "list[string]", required=True),
            TransformInputSchema("separator", "string", required=False, description="Word separator"),
        ],
        output_schema=TransformOutputSchema("string", "Word-reversed string"),
        resolver=lambda inputs, separator=" ": " ".join(
            " ".join(str(i) for i in inputs).split(separator)[::-1]
        ),
        deterministic=True,
    ))

    # reverse: Reverse a single input
    registry.register(TransformSpec(
        transform_id="reverse",
        display_name="Reverse",
        description="Reverse a single string input",
        input_schema=[
            TransformInputSchema("input", "string", required=True),
        ],
        output_schema=TransformOutputSchema("string", "Reversed string"),
        resolver=lambda input: str(input)[::-1],
        deterministic=True,
    ))


def register_default_actions(registry: ActionRegistry) -> None:
    """Register all built-in actions."""

    # write_file action
    registry.register(ActionSpec(
        action_type="write_file",
        display_name="Write File",
        description="Write content to a file",
        capabilities=[
            Capability(
                capability_id="file_write",
                description="Can write to files",
                input_types={"file_path", "content"},
                output_types={"file_created"},
                side_effects={"file_modified"},
            ),
        ],
        required_capabilities=["file_write"],
        version="1.0.0",
    ))

    # read_file action
    registry.register(ActionSpec(
        action_type="read_file",
        display_name="Read File",
        description="Read content from a file",
        capabilities=[
            Capability(
                capability_id="file_read",
                description="Can read from files",
                input_types={"file_path"},
                output_types={"file_content"},
                side_effects=set(),
            ),
        ],
        required_capabilities=["file_read"],
        version="1.0.0",
    ))

    # list_dir action
    registry.register(ActionSpec(
        action_type="list_dir",
        display_name="List Directory",
        description="List contents of a directory",
        capabilities=[
            Capability(
                capability_id="directory_list",
                description="Can list directory contents",
                input_types={"directory_path"},
                output_types={"directory_listing"},
                side_effects=set(),
            ),
        ],
        required_capabilities=["directory_list"],
        version="1.0.0",
    ))


def register_default_tools(registry: ToolCapabilityRegistry) -> None:
    """Register all built-in tools with their actual implementations."""
    
    # Import actual tool implementations
    from tools.write_file import write_file
    from tools.read_file import read_file
    from tools.list_dir import list_dir

    # write_file tool
    registry.register(ToolSpec(
        tool_id="write_file",
        display_name="Write File",
        description="Write content to a file",
        executor=write_file,
        capabilities=[
            ToolCapability(
                capability_id="file_write",
                description="Can write to files",
                input_schema={
                    "filename": {"type": "string", "required": True, "description": "File path"},
                    "content": {"type": "string", "required": True, "description": "File content"},
                },
                output_schema={
                    "file": {"type": "string"},
                    "bytes_written": {"type": "integer"},
                },
                effects=[
                    ToolEffect(
                        effect_type=EffectType.WRITE,
                        resource_type="file",
                        description="Writes content to a file",
                        reversible=False,
                    ),
                ],
                produces_types={"file_created"},
                consumes_types={"file_path", "content"},
            ),
        ],
        safety_level=SafetyLevel.CAUTIOUS,
        version="1.0.0",
    ))

    # read_file tool
    registry.register(ToolSpec(
        tool_id="read_file",
        display_name="Read File",
        description="Read content from a file",
        executor=read_file,
        capabilities=[
            ToolCapability(
                capability_id="file_read",
                description="Can read from files",
                input_schema={
                    "filename": {"type": "string", "required": True, "description": "File path"},
                },
                output_schema={
                    "file": {"type": "string"},
                    "content": {"type": "string"},
                },
                effects=[
                    ToolEffect(
                        effect_type=EffectType.READ,
                        resource_type="file",
                        description="Reads content from a file",
                        reversible=True,
                    ),
                ],
                produces_types={"file_content"},
                consumes_types={"file_path"},
            ),
        ],
        safety_level=SafetyLevel.SAFE,
        version="1.0.0",
    ))

    # list_dir tool
    registry.register(ToolSpec(
        tool_id="list_dir",
        display_name="List Directory",
        description="List contents of a directory",
        executor=list_dir,
        capabilities=[
            ToolCapability(
                capability_id="directory_list",
                description="Can list directory contents",
                input_schema={
                    "path": {"type": "string", "required": True, "description": "Directory path"},
                },
                output_schema={
                    "path": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                },
                effects=[
                    ToolEffect(
                        effect_type=EffectType.QUERY,
                        resource_type="directory",
                        description="Lists directory contents",
                        reversible=True,
                    ),
                ],
                produces_types={"directory_listing"},
                consumes_types={"directory_path"},
            ),
        ],
        safety_level=SafetyLevel.SAFE,
        version="1.0.0",
    ))


def register_default_validation_rules(registry: ValidationRuleRegistry) -> None:
    """Register all built-in validation rules."""

    # Topology validation rule
    registry.register(ValidationRule(
        rule_id="topology_check",
        display_name="DAG Topology Check",
        description="Validates DAG has no cycles, orphans, and is fully connected",
        category=ValidationCategory.STRUCTURAL,
        default_severity=ValidationSeverity.ERROR,
        validator=lambda ctx: [],  # Placeholder - actual implementation in validation layer
        applies_to=["pre_execution", "post_execution"],
        version="1.0.0",
    ))

    # Schema validation rule
    registry.register(ValidationRule(
        rule_id="schema_validation",
        display_name="Tool Schema Validation",
        description="Validates all tool arguments match their schemas",
        category=ValidationCategory.STRUCTURAL,
        default_severity=ValidationSeverity.ERROR,
        validator=lambda ctx: [],  # Placeholder
        applies_to=["pre_execution"],
        version="1.0.0",
    ))

    # Trace fidelity rule
    registry.register(ValidationRule(
        rule_id="trace_fidelity",
        display_name="Trace Fidelity Check",
        description="Validates execution trace matches planned DAG",
        category=ValidationCategory.TRACE,
        default_severity=ValidationSeverity.ERROR,
        validator=lambda ctx: [],  # Placeholder
        applies_to=["post_execution"],
        version="1.0.0",
    ))


def initialize_default_registries() -> Dict[str, Any]:
    """
    Create and populate all default registries.
    
    Returns:
        Dictionary with keys: transforms, actions, tools, validation
    """
    transform_registry = TransformRegistry()
    action_registry = ActionRegistry()
    tool_registry = ToolCapabilityRegistry()
    validation_registry = ValidationRuleRegistry()

    register_default_transforms(transform_registry)
    register_default_actions(action_registry)
    register_default_tools(tool_registry)
    register_default_validation_rules(validation_registry)

    return {
        "transforms": transform_registry,
        "actions": action_registry,
        "tools": tool_registry,
        "validation": validation_registry,
    }