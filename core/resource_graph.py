from typing import Dict, Optional


class ResourceGraph:
    """
    v1 Resource Graph

    Purpose:
    - Canonical mapping of logical → physical resources
    - Prevents file identity drift across DAG steps
    """

    def __init__(self):

        # logical → physical mapping
        self.resources: Dict[str, str] = {}

        # reverse lookup (optional debugging)
        self.reverse: Dict[str, str] = {}

    # =====================================================
    # REGISTER RESOURCE
    # =====================================================

    def register(self, logical_name: str, physical_path: str):

        self.resources[logical_name] = physical_path
        self.reverse[physical_path] = logical_name

    # =====================================================
    # RESOLVE RESOURCE
    # =====================================================

    def resolve(self, name: str) -> str:

        # already physical path
        if "/" in name:
            return name

        return self.resources.get(name, name)

    # =====================================================
    # CHECK EXISTENCE
    # =====================================================

    def has(self, name: str) -> bool:

        return name in self.resources

    # =====================================================
    # DEBUG
    # =====================================================

    def dump(self):

        return {
            "logical_to_physical": self.resources,
            "physical_to_logical": self.reverse
        }