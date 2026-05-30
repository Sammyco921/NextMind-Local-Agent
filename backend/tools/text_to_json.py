import json


def text_to_json(text: str) -> dict:
    """Deterministic text-to-JSON transform: wraps text in a JSON structure."""
    return {
        "status": "success",
        "data": {"content": text, "length": len(text)},
    }
