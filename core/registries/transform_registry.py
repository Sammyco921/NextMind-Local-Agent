# core/registries/transform_registry.py
"""
Registry for data transforms used in artifact resolution.

Transforms are deterministic functions that convert input artifacts
into output values. They are used during execution to process data
flowing between DAG nodes.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from core.registries.base import Registry


@dataclass(frozen=True)
class TransformInputSchema:
    """Schema definition for a transform input."""
    field_name: str
    field_type: str  # e.g., "string", "list[string]", "artifact_ref"
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class TransformOutputSchema:
    """Schema definition for a transform output."""
    output_type: str  # e.g., "string", "file_content"
    description: str = ""


@dataclass(frozen=True)
class TransformSpec:
    """
    Complete specification for a data transform.
    
    Transforms are deterministic functions that convert input artifacts
    into output values. They are used during artifact resolution.
    """
    transform_id: str
    display_name: str
    description: str
    input_schema: List[TransformInputSchema]
    output_schema: TransformOutputSchema
    resolver: Callable[..., Any]  # The actual transform function
    validator: Optional[Callable[..., List[str]]] = None  # Optional validation
    deterministic: bool = True  # Must be True for production
    version: str = "1.0.0"


class TransformRegistry(Registry[TransformSpec]):
    """
    Registry for data transforms.
    
    Example usage:
        registry = TransformRegistry()
        registry.register(TransformSpec(
            transform_id="combine_reverse",
            display_name="Combine and Reverse",
            description="Combines multiple inputs and reverses the result",
            input_schema=[
                TransformInputSchema("inputs", "list[string]", required=True),
            ],
            output_schema=TransformOutputSchema("string", "Reversed combined string"),
            resolver=lambda inputs: "".join(inputs)[::-1],
        ))
    """

    def __init__(self):
        self._transforms: Dict[str, TransformSpec] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self, spec: TransformSpec, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if spec.transform_id in self._transforms:
            raise ValueError(f"Transform already registered: {spec.transform_id}")
        if not spec.deterministic:
            raise ValueError(f"Non-deterministic transforms not allowed: {spec.transform_id}")
        if not spec.input_schema:
            raise ValueError(f"Transform must have at least one input: {spec.transform_id}")
        
        self._transforms[spec.transform_id] = spec
        if metadata:
            self._metadata[spec.transform_id] = metadata

    def get(self, transform_id: str) -> TransformSpec:
        if transform_id not in self._transforms:
            raise KeyError(f"Unknown transform: {transform_id}")
        return self._transforms[transform_id]

    def has(self, transform_id: str) -> bool:
        return transform_id in self._transforms

    def keys(self) -> List[str]:
        return sorted(self._transforms.keys())

    def validate(self, transform_id: str, context: Dict[str, Any]) -> List[str]:
        if transform_id not in self._transforms:
            return [f"Unknown transform: {transform_id}"]

        spec = self._transforms[transform_id]
        errors: List[str] = []

        # Check required inputs are present
        for input_spec in spec.input_schema:
            if input_spec.required and input_spec.field_name not in context:
                errors.append(f"Missing required input: {input_spec.field_name}")

        # Run spec-specific validator
        if spec.validator:
            errors.extend(spec.validator(context))

        return errors

    def get_metadata(self, key: str) -> Dict[str, Any]:
        return self._metadata.get(key, {})

    def execute(self, transform_id: str, inputs: Dict[str, Any]) -> Any:
        """
        Execute a transform with the given inputs.
        
        Args:
            transform_id: The transform to execute
            inputs: Input values matching the transform's input schema
            
        Returns:
            The transform output
            
        Raises:
            ValueError: If inputs don't match the schema
            KeyError: If transform is not found
        """
        spec = self.get(transform_id)

        # Validate inputs
        for input_spec in spec.input_schema:
            if input_spec.required and input_spec.field_name not in inputs:
                raise ValueError(f"Missing required input: {input_spec.field_name}")

        # Execute the transform
        return spec.resolver(**inputs)