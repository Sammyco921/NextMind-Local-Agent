from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.execution_mode import ExecutionMode
from core.memory.agent_context_api import AgentContextAPI
from core.memory.context_weighting import ContextWeightingSystem
from core.memory.continuity import ContinuityDetector
from core.memory.decision_store import DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackStore
from core.memory.goal_registry import GoalRegistry
from core.memory.project_view import ProjectIntelligenceView
from core.strict_pipeline import StrictPipeline
from core.tool_registry import ToolRegistry
from core.tool_schemas import TOOL_SCHEMAS
from execution_feed import build_result_summary, build_status_line, collect_steps, event_to_step
from tools.inject_failure import INJECT_FAILURE_TOOL, inject_failure
from tools.list_dir import list_dir
from tools.read_file import read_file
from tools.write_file import write_file

_EXEC_MEMORY = ExecutionMemoryStore(jsonl_path=os.path.join(ROOT, "memory", "execution_events.jsonl"))
_GOALS = GoalRegistry()
_DECISIONS = DecisionStore(jsonl_path=os.path.join(ROOT, "memory", "decisions.jsonl"))
_FEEDBACK = FeedbackStore(jsonl_path=os.path.join(ROOT, "memory", "feedback.jsonl"))
_WEIGHTING = ContextWeightingSystem(feedback_store=_FEEDBACK)
_CONTINUITY = ContinuityDetector(goal_registry=_GOALS, execution_store=_EXEC_MEMORY, feedback_store=_FEEDBACK)
_PROJECT_VIEW = ProjectIntelligenceView(
    goal_registry=_GOALS, decision_store=_DECISIONS,
    execution_store=_EXEC_MEMORY, feedback_store=_FEEDBACK,
)
_API = AgentContextAPI(execution_store=_EXEC_MEMORY, decision_store=_DECISIONS, goal_registry=_GOALS, weighting_system=_WEIGHTING)
_PIPELINE_LOCK = threading.Lock()


def _bootstrap_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    reg.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    reg.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])
    reg.register(INJECT_FAILURE_TOOL, inject_failure, TOOL_SCHEMAS.get(INJECT_FAILURE_TOOL, {}))
    return reg


app = FastAPI(title="NextMind", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/goal")
async def submit_goal(body: dict) -> Dict[str, Any]:
    goal_text = (body.get("goal") or "").strip()
    if not goal_text:
        return JSONResponse(status_code=400, content={"error": "Goal text is required"})

    registry = _bootstrap_registry()
    pipeline = StrictPipeline(
        registry,
        execution_memory=_EXEC_MEMORY,
        goal_registry=_GOALS,
        decision_store=_DECISIONS,
        feedback_store=_FEEDBACK,
        continuity_detector=_CONTINUITY,
    )

    event_count_before = len(_EXEC_MEMORY.get_events())

    with _PIPELINE_LOCK:
        result = pipeline.run(goal_text, mode=ExecutionMode.NORMAL)

    steps = collect_steps(_EXEC_MEMORY)
    result_dict = result.to_dict()
    response = {
        "status": result_dict.get("status", "unknown"),
        "summary": build_result_summary(result_dict),
        "status_line": build_status_line(steps),
        "steps": steps,
        "result": result_dict,
    }
    continuation = getattr(result, "continuation", None) or result_dict.get("continuation")
    if continuation:
        response["continuation"] = continuation
    return response


@app.get("/api/analytics")
async def analytics() -> Dict[str, Any]:
    goals = _GOALS.list_goals()
    decisions = _DECISIONS.get_decisions()
    feedback = _FEEDBACK.get_records()
    events = _EXEC_MEMORY.get_events()

    total_goals = len(goals)
    active = sum(1 for g in goals if g.lifecycle_state == "active")
    completed = sum(1 for g in goals if g.lifecycle_state == "completed")
    failed = sum(1 for g in goals if g.lifecycle_state in ("failed", "blocked"))

    total_feedback = len(feedback)
    success_count = sum(1 for r in feedback if r.outcome == "success")
    failure_count = sum(1 for r in feedback if r.outcome in ("failed", "blocked"))
    failure_rate = (failure_count / total_feedback * 100) if total_feedback > 0 else 0.0

    error_patterns: Dict[str, int] = {}
    for ev in events:
        err = ev.get("error")
        if err:
            err = str(err)[:80]
            error_patterns[err] = error_patterns.get(err, 0) + 1
    sorted_patterns = sorted(error_patterns.items(), key=lambda x: -x[1])[:10]

    goal_lifecycle: List[Dict[str, Any]] = []
    for g in goals:
        goal_lifecycle.append({
            "description": g.description[:60],
            "status": g.lifecycle_state,
        })

    return {
        "goals": {
            "total": total_goals,
            "active": active,
            "completed": completed,
            "failed": failed,
        },
        "feedback": {
            "total": total_feedback,
            "successes": success_count,
            "failures": failure_count,
            "failure_rate": round(failure_rate, 1),
        },
        "failure_patterns": [{"error": err, "count": cnt} for err, cnt in sorted_patterns],
        "goal_lifecycle": goal_lifecycle,
        "total_execution_events": len(events),
    }


@app.get("/api/debug/events")
async def debug_events() -> List[Dict[str, Any]]:
    return _EXEC_MEMORY.get_events()


@app.get("/api/debug/decisions")
async def debug_decisions() -> List[Dict[str, Any]]:
    return [d.to_dict() for d in _DECISIONS.get_decisions()]


@app.get("/api/debug/feedback")
async def debug_feedback() -> List[Dict[str, Any]]:
    return [r.to_dict() for r in _FEEDBACK.get_records()]


@app.get("/api/project")
async def project_view(lens: str = "overview") -> Dict[str, Any]:
    if lens == "history":
        return _PROJECT_VIEW.history()
    elif lens == "continuity":
        return _PROJECT_VIEW.continuity()
    return _PROJECT_VIEW.overview()


connected_clients: set = set()


@app.websocket("/ws/feed")
async def ws_feed(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        data = await websocket.receive_text()
        msg = json.loads(data)
        goal_text = (msg.get("goal") or "").strip()
        if not goal_text:
            await websocket.send_json({"type": "error", "message": "Goal text is required"})
            return

        registry = _bootstrap_registry()
        pipeline = StrictPipeline(
            registry,
            execution_memory=_EXEC_MEMORY,
            goal_registry=_GOALS,
            decision_store=_DECISIONS,
            feedback_store=_FEEDBACK,
        )

        event_count_before = len(_EXEC_MEMORY.get_events())
        result_container: list = []
        exception_container: list = []

        def run():
            try:
                r = pipeline.run(goal_text, mode=ExecutionMode.NORMAL)
                result_container.append(r)
            except Exception as e:
                exception_container.append(e)

        t = threading.Thread(target=run, daemon=True)
        t.start()

        while t.is_alive():
            current_events = _EXEC_MEMORY.get_events()
            for ev in current_events[event_count_before:]:
                step = event_to_step(ev)
                await websocket.send_json({"type": "step", "step": step})
                event_count_before = len(current_events)
            await asyncio.sleep(0.1)

        for ev in _EXEC_MEMORY.get_events()[event_count_before:]:
            step = event_to_step(ev)
            await websocket.send_json({"type": "step", "step": step})

        if exception_container:
            await websocket.send_json({"type": "error", "message": str(exception_container[0])})
            return

        result = result_container[0]
        steps = collect_steps(_EXEC_MEMORY)
        result_dict = result.to_dict()
        ws_result: dict = {
            "type": "result",
            "status": result_dict.get("status", "unknown"),
            "summary": build_result_summary(result_dict),
            "status_line": build_status_line(steps),
            "steps": steps,
            "result": result_dict,
        }
        continuation = getattr(result, "continuation", None) or result_dict.get("continuation")
        if continuation:
            ws_result["continuation"] = continuation
        await websocket.send_json(ws_result)
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)


FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
@app.get("/analytics")
@app.get("/project")
@app.get("/debug")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": "Frontend not built"})


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    uvicorn.run("api_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()
