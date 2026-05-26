# core/registries/base.py
"""
Base registry interface for all NextMind v2.0 component registries.

All registries must:
- Be deterministic (keys() returns sorted list)
- Validate components before registration
- Raise KeyError/ValueError for missing/invalid components
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar, Optional, List

T = TypeVar("T")


class Registry(ABC, Generic[T]):
    """
    Base registry interface for all component registries.
    
    Provides a consistent API for registering, retrieving, and validating
    components across all registry types.
    """

    @abstractmethod
    def register(
        self, key: str, value: T, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a component.
        
        Args:
            key: Unique identifier for the component
            value: The component to register
            metadata: Optional metadata about the component
            
        Raises:
            ValueError: If the component is already registered or invalid
        """
        pass

    @abstractmethod
    def get(self, key: str) -> T:
        """
        Get a registered component.
        
        Args:
            key: The component identifier
            
        Returns:
            The registered component
            
        Raises:
            KeyError: If the component is not found
        """
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check if a component is registered.
        
        Args:
            key: The component identifier
            
        Returns:
            True if the component is registered, False otherwise
        """
        pass

    @abstractmethod
    def keys(self) -> List[str]:
        """
        Get all registered component keys.
        
        Returns:
            Sorted list of all registered keys (for determinism)
        """
        pass

    @abstractmethod
    def validate(self, key: str, context: Dict[str, Any]) -> List[str]:
        """
        Validate a component against a context.
        
        Args:
            key: The component identifier
            context: Context for validation (e.g., available capabilities)
            
        Returns:
            List of validation error messages (empty if valid)
        """
        pass

    def get_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get metadata for a registered component.
        
        Args:
            key: The component identifier
            
        Returns:
            Metadata dictionary (empty dict if no metadata)
        """
        return {}

    def __contains__(self, key: str) -> bool:
        """Support 'key in registry' syntax."""
        return self.has(key)

    def __iter__(self):
        """Iterate over registered keys (sorted for determinism)."""
        return iter(self.keys())

    def __len__(self) -> int:
        """Get the number of registered components."""
        return len(self.keys())