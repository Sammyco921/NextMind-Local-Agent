import json


def json_to_text(json_data: dict) -> str:
    """Deterministic JSON-to-text transform: serializes JSON to pretty-printed string."""
    return {
        "status": "success",
        "content": json.dumps(json_data, indent=2, sort_keys=True),
    }
