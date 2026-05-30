from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict


def build_event(
    dag_id: str,
    goal_id: str,
    node_id: str,
    tool: str,
    args: Dict[str, Any],
    status: str,
    output: Any = None,
    error: str | None = None,
) -> Dict[str, Any]:
    return {
        "event_id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dag_id": dag_id,
        "goal_id": goal_id,
        "node_id": node_id,
        "tool": tool,
        "args": args,
        "status": status,
        "output": output,
        "error": error,
    }
