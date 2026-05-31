import traceback
import json
import os

from .taxonomy import FailureCategory, FailureRecord, SOURCE_LAYER_NAMES


SAFE_MESSAGES: dict[str, str] = {
    "FileNotFoundError": "A required file or resource was not found. The system continues with available data.",
    "JSONDecodeError": "A data file could not be read. The system continues with an empty state.",
    "json.JSONDecodeError": "A data file could not be read. The system continues with an empty state.",
    "json.decoder.JSONDecodeError": "A data file could not be read. The system continues with an empty state.",
    "PermissionError": "A file permission issue was detected. The system continues with available data.",
    "OSError": "A filesystem error occurred. The system continues running.",
    "KeyError": "An internal data lookup failed. The system continues with available data.",
    "IndexError": "An internal data access failed. The system continues with available data.",
    "TypeError": "An internal type mismatch occurred. The system continues with available data.",
    "ValueError": "An internal value error occurred. The system continues with available data.",
    "AttributeError": "An internal attribute error occurred. The system continues running.",
    "ImportError": "An optional module is missing. The system continues with reduced capability.",
    "ConnectionError": "A connection error occurred. The system continues running.",
    "TimeoutError": "An operation timed out. The system continues running.",
}

CATEGORY_MAP: dict[str, FailureCategory] = {
    "dag_executor": FailureCategory.EXECUTION_FAILURE,
    "tool_registry": FailureCategory.EXECUTION_FAILURE,
    "pipeline": FailureCategory.EXECUTION_FAILURE,
    "memory_store": FailureCategory.CONTEXT_FAILURE,
    "decision_store": FailureCategory.CONTEXT_FAILURE,
    "feedback_store": FailureCategory.CONTEXT_FAILURE,
    "goal_registry": FailureCategory.CONTEXT_FAILURE,
    "context_weighting": FailureCategory.CONTEXT_FAILURE,
    "context_synthesizer": FailureCategory.CONTEXT_FAILURE,
    "agent_context": FailureCategory.CONTEXT_FAILURE,
    "project_view": FailureCategory.CONTEXT_FAILURE,
    "continuity": FailureCategory.CONTEXT_FAILURE,
    "structure_lens": FailureCategory.CONTEXT_FAILURE,
    "relationship_lens": FailureCategory.CONTEXT_FAILURE,
    "change_lens": FailureCategory.CONTEXT_FAILURE,
    "activity_lens": FailureCategory.CONTEXT_FAILURE,
    "workspace_resolver": FailureCategory.WORKSPACE_FAILURE,
    "workspace_gateway": FailureCategory.WORKSPACE_FAILURE,
    "workspace_tracker": FailureCategory.WORKSPACE_FAILURE,
    "session_store": FailureCategory.WORKSPACE_FAILURE,
    "session_manager": FailureCategory.WORKSPACE_FAILURE,
    "command_router": FailureCategory.API_FAILURE,
    "handoff_builder": FailureCategory.API_FAILURE,
    "api_server": FailureCategory.API_FAILURE,
    "agent_interface": FailureCategory.API_FAILURE,
}


def normalize_exception(exc: BaseException, source_layer: str = "unknown") -> FailureRecord:
    exc_type = type(exc).__qualname__
    safe_msg = SAFE_MESSAGES.get(exc_type, f"An internal error occurred in {source_layer}. The system continues running.")
    category = CATEGORY_MAP.get(source_layer, FailureCategory.UNKNOWN_FAILURE)
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return FailureRecord(
        category=category,
        source_layer=source_layer,
        safe_message=safe_msg,
        debug_payload={"exception_type": exc_type, "traceback": tb},
        original_exception=str(exc),
    )


def normalize_dict(error: dict, source_layer: str = "unknown") -> FailureRecord:
    category = CATEGORY_MAP.get(source_layer, FailureCategory.UNKNOWN_FAILURE)
    return FailureRecord(
        category=category,
        source_layer=source_layer,
        safe_message=error.get("safe_message", "An internal error occurred."),
        debug_payload=error.get("debug_payload"),
        original_exception=error.get("original_exception"),
    )


def safe_message_for_file(path: str) -> str:
    basename = os.path.basename(path) if path else "file"
    return f"A data file ('{basename}') could not be read. The system continues with an empty state."
