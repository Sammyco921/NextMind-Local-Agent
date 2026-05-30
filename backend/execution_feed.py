from __future__ import annotations

from typing import Any, Dict, List

from core.memory.execution_memory_store import ExecutionMemoryStore


STEP_KEYWORDS: Dict[str, str] = {
    "write_file": "Writing file",
    "read_file": "Reading file",
    "list_dir": "Listing directory contents",
    "inject_failure": "Running diagnostic step",
    "json_to_text": "Converting data",
    "text_to_json": "Converting data",
    "file_to_text": "Reading content",
}


def event_to_step(event: dict) -> dict:
    tool = event.get("tool", "")
    action = STEP_KEYWORDS.get(tool, f"Running {tool}" if tool else "Working")
    return {
        "id": event.get("node_id", ""),
        "label": f"{action}...",
        "status": event.get("status", ""),
        "error": event.get("error"),
        "tool": tool,
    }


def collect_steps(store: ExecutionMemoryStore) -> List[dict]:
    events = store.get_events()
    if not events:
        return []
    last_goal_id = events[-1].get("goal_id", "")
    goal_events = [e for e in events if e.get("goal_id") == last_goal_id]
    seen: set = set()
    steps: list = []
    for e in goal_events:
        nid = e.get("node_id", "")
        if nid and nid not in seen:
            seen.add(nid)
            steps.append(event_to_step(e))
    return steps


def build_result_summary(result_dict: dict) -> str:
    status = result_dict.get("status", "unknown")
    if status == "success":
        steps = result_dict.get("execution", {}).get("steps_executed", 0)
        return f"Completed successfully ({steps} steps executed)."
    if status == "failed":
        stage = result_dict.get("failed_stage", "execution")
        return f"Stopped during: {stage}."
    if status == "clarification_required":
        return "The request was unclear. Please be more specific."
    return f"Status: {status}."


def build_status_line(steps: List[dict]) -> str:
    total = len(steps)
    successes = sum(1 for s in steps if s["status"] == "success")
    failures = sum(1 for s in steps if s["status"] == "failed")
    if failures > 0:
        return f"{total} steps — {successes} completed, {failures} had issues"
    return f"{total} steps completed successfully"
