def file_to_text(file_data: dict) -> dict:
    """Deterministic file-to-text transform: extracts content from file artifact."""
    content = file_data.get("content", "")
    return {
        "status": "success",
        "content": content,
    }
