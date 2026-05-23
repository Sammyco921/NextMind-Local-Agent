# core/import_guard.py

import sys
import importlib
from typing import List, Dict, Set


# =====================================================
# IMPORT GUARD CONFIGURATION
# =====================================================

class ImportRules:
    """
    Defines allowed and forbidden import boundaries.
    """

    # Core modules are NEVER allowed to import legacy
    CORE_PREFIX = "core"

    # Legacy is completely isolated
    LEGACY_PREFIX = "legacy"

    # Explicit forbidden cross-boundary imports
    FORBIDDEN_IMPORTS: Dict[str, List[str]] = {
        "core": ["legacy"],
    }

    # Optional: enforce allowed-only imports in core (strict mode)
    STRICT_CORE_MODE = True


# =====================================================
# IMPORT GUARD ENGINE
# =====================================================

class ImportGuard:
    """
    Runtime + static import boundary enforcement.

    Use:
        ImportGuard.enforce(__name__)
    """

    _seen_stack: Set[str] = set()

    @staticmethod
    def enforce(module_name: str) -> None:
        """
        Call at top of every core module.
        Detects illegal import patterns early.
        """

        ImportGuard._detect_cycles(module_name)
        ImportGuard._enforce_boundaries(module_name)

    # -------------------------------------------------
    # CIRCULAR IMPORT DETECTION
    # -------------------------------------------------

    @staticmethod
    def _detect_cycles(module_name: str) -> None:

        if module_name in ImportGuard._seen_stack:
            raise ImportError(
                f"[ImportGuard] Circular import detected: {module_name}"
            )

        ImportGuard._seen_stack.add(module_name)

    # -------------------------------------------------
    # LAYER BOUNDARY ENFORCEMENT
    # -------------------------------------------------

    @staticmethod
    def _enforce_boundaries(module_name: str) -> None:

        if not ImportRules.STRICT_CORE_MODE:
            return

        # Determine module layer
        if module_name.startswith(ImportRules.CORE_PREFIX):

            # Scan sys.modules for illegal imports
            for mod in list(sys.modules.keys()):

                if mod.startswith(ImportRules.LEGACY_PREFIX):

                    raise ImportError(
                        f"[ImportGuard] Illegal dependency detected:\n"
                        f"  {module_name} → {mod}\n"
                        f"  Core layer cannot import legacy modules."
                    )

    # -------------------------------------------------
    # SAFE IMPORT WRAPPER (optional future use)
    # -------------------------------------------------

    @staticmethod
    def safe_import(module_path: str):
        """
        Controlled import mechanism for dynamic loading.
        """

        ImportGuard._validate_import_path(module_path)
        return importlib.import_module(module_path)

    # -------------------------------------------------
    # IMPORT PATH VALIDATION
    # -------------------------------------------------

    @staticmethod
    def _validate_import_path(module_path: str):

        if ImportRules.STRICT_CORE_MODE:

            if ImportRules.LEGACY_PREFIX in module_path.split("."):

                raise ImportError(
                    f"[ImportGuard] Blocked import of legacy module: {module_path}"
                )