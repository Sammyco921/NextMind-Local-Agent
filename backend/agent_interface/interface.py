from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from agent_interface.contracts import (
    AmbiguityState,
    ContextScope,
    InputContract,
    OutputContract,
    OutputMeta,
)
from agent_interface.context_packager import ContextPackager
from agent_interface.os_context import OSContext
from agent_interface.trace_compressor import TraceCompressor
from core.commands import CommandRouter
from core.session import SessionManager
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
from core.structure.change_store import ChangeStore
from core.structure.project_catalog import ProjectCatalog
from core.structure.component_registry import ComponentRegistry
from core.structure.goal_impact_tracker import GoalImpactTracker
from core.structure.relationship_store import RelationshipStore
from core.tool_registry import ToolRegistry
from core.tool_schemas import TOOL_SCHEMAS
from execution_feed import build_result_summary, collect_steps
from tools.inject_failure import INJECT_FAILURE_TOOL, inject_failure
from tools.list_dir import list_dir
from tools.read_file import read_file
from tools.write_file import write_file


class AgentInterface:
    """Unified agent interface for all external surfaces.

    Single entry point for CLI, API, and UI. All interactions conform to the
    InputContract / OutputContract structure. Context is resolved exclusively
    through ContextPackager (ProjectIntelligenceView). No raw store objects
    are exposed externally.

    System boundary enforcement:
    - UI cannot modify execution behavior
    - API cannot bypass pipeline
    - CLI cannot access internal stores directly
    - Context system cannot influence DAG execution
    - Memory systems remain strictly observational
    - Project View remains read-only aggregation layer
    """

    def __init__(
        self,
        exec_memory: ExecutionMemoryStore,
        goals: GoalRegistry,
        decisions: DecisionStore,
        feedback: FeedbackStore,
        weighting: ContextWeightingSystem,
        continuity: ContinuityDetector,
        project_view: ProjectIntelligenceView,
        api: AgentContextAPI,
        catalog: ProjectCatalog | None = None,
        component_registry: ComponentRegistry | None = None,
        impact_tracker: GoalImpactTracker | None = None,
        change_store: ChangeStore | None = None,
        relationship_store: RelationshipStore | None = None,
    ) -> None:
        self._exec_memory = exec_memory
        self._goals = goals
        self._decisions = decisions
        self._feedback = feedback
        self._weighting = weighting
        self._continuity = continuity
        self._project_view = project_view
        self._api = api
        self._catalog = catalog
        self._component_registry = component_registry
        self._impact_tracker = impact_tracker
        self._change_store = change_store
        self._relationship_store = relationship_store

        self.context = ContextPackager(project_view)
        self.trace = TraceCompressor(exec_memory)
        self._os_context: OSContext | None = None
        self._router = CommandRouter()
        sessions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sessions")
        self._sessions = SessionManager(data_dir=sessions_dir)
        self.context.set_session_info(self._sessions.get_workspace_info())

    def _bootstrap_registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        reg.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
        reg.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
        reg.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])
        reg.register(INJECT_FAILURE_TOOL, inject_failure, TOOL_SCHEMAS.get(INJECT_FAILURE_TOOL, {}))
        return reg

    def _resolve_ambiguity_state(
        self,
        result_dict: Dict[str, Any],
        continuation: Optional[Dict[str, Any]] = None,
    ) -> AmbiguityState:
        status = result_dict.get("status", "")
        if continuation and continuation.get("is_continuation"):
            return "mapped_to_existing_goal"
        if status == "clarification_required":
            return "requires_clarification"
        if status == "success":
            stages = result_dict.get("stages", [])
            for s in stages:
                if s.get("stage") == "human_normalization":
                    detail = s.get("detail", "")
                    if detail and detail != "no changes":
                        return "normalized"
            return "resolved"
        return "normalized"

    def process_input(self, contract: InputContract) -> OutputContract:
        goal_text = contract.goal.strip()
        mode = ExecutionMode.NORMAL
        if contract.mode in ("stress_test", "failure_injection"):
            mode = ExecutionMode(contract.mode)
        # "observe" and "explain" are interface-level abstractions;
        # both map to NORMAL execution at the engine level.

        registry = self._bootstrap_registry()
        pipeline = StrictPipeline(
            registry,
            execution_memory=self._exec_memory,
            goal_registry=self._goals,
            decision_store=self._decisions,
            feedback_store=self._feedback,
            continuity_detector=self._continuity,
        )

        start = time.time()
        result = pipeline.run(goal_text, mode=mode)
        elapsed = (time.time() - start) * 1000

        result_dict = result.to_dict()
        status = result_dict.get("status", "unknown")
        continuation = getattr(result, "continuation", None) or result_dict.get("continuation")

        goal_id = ""
        if self._goals:
            all_goals = self._goals.list_goals()
            if all_goals:
                goal_id = all_goals[-1].goal_id

        trace = self.trace.compress(result_dict)
        ambiguity_state = self._resolve_ambiguity_state(result_dict, continuation)

        if status == "success" and goal_id:
            if self._impact_tracker:
                self._record_impacts(goal_id, goal_text)
            if self._change_store:
                self._record_changes(goal_id, goal_text)
            if self._relationship_store:
                self._record_relationships(goal_id, goal_text)

        result_data: Dict[str, Any] = {}
        if status == "clarification_required":
            clar = result_dict.get("clarification", {})
            result_data = {
                "type": "clarification_required",
                "questions": clar.get("clarification_questions", []),
                "warnings": list(clar.get("ambiguity_warnings", [])),
            }
        elif status == "success":
            result_data = {
                "type": "execution_result",
                "status": status,
            }
        else:
            result_data = {
                "type": "error",
                "failed_stage": result_dict.get("failed_stage", ""),
                "reason": result_dict.get("failure", {}).get("reason", ""),
            }

        return OutputContract(
            result=result_data,
            trace=trace,
            continuation=continuation if isinstance(continuation, dict) else None,
            meta=OutputMeta(
                timing_ms=round(elapsed, 1),
                goal_id=goal_id,
                mode=contract.mode,
                status=status,
                ambiguity_state=ambiguity_state,
            ),
        )

    def process(
        self,
        goal: str,
        mode: str = "execute",
        context_scope: Optional[ContextScope] = None,
    ) -> OutputContract:
        contract = InputContract(
            goal=goal,
            context_scope=context_scope,
            mode=mode,
        )
        return self.process_input(contract)

    def get_os_context(self) -> Optional[OSContext]:
        return self._os_context

    def set_os_context(self, os_context: OSContext) -> None:
        self._os_context = os_context

    def get_project_view(self, lens: str = "overview") -> Dict[str, Any]:
        return self.context.get_lens(lens)

    def get_handoff(self, mode: str = "standard") -> Dict[str, Any]:
        return self.context.get_handoff(mode=mode)

    def get_workspace_activity(self) -> Dict[str, Any]:
        return self.context.get_workspace()

    def _sync_session_info(self) -> None:
        self.context.set_session_info(self._sessions.get_workspace_info())

    def get_current_workspace(self) -> Dict[str, Any]:
        return self._sessions.get_current_workspace()

    def switch_workspace(self, name: str) -> Dict[str, Any]:
        result = self._sessions.switch_workspace(name)
        self._sync_session_info()
        return result

    def list_workspaces(self) -> List[Dict[str, Any]]:
        return self._sessions.list_workspaces()

    def create_workspace(self, name: str) -> Dict[str, Any]:
        result = self._sessions.create_workspace(name)
        self._sync_session_info()
        return result

    def get_handoff_markdown(self, mode: str = "standard") -> str:
        return self.context.get_handoff_markdown(mode=mode)

    def file_create(self, path: str, content: str, context: str = "auto") -> Dict[str, Any]:
        if self._os_context is None:
            return {"status": "error", "error": "OS context not initialized"}
        try:
            return self._os_context.gateway.create(path, content, context=context)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def file_read(self, path: str, context: str = "auto") -> Dict[str, Any]:
        if self._os_context is None:
            return {"status": "error", "error": "OS context not initialized"}
        try:
            return self._os_context.gateway.read(path, context=context)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def file_list(self, path: str = ".", context: str = "auto") -> Dict[str, Any]:
        if self._os_context is None:
            return {"status": "error", "error": "OS context not initialized"}
        try:
            return self._os_context.gateway.list_dir(path, context=context)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_analytics(self) -> Dict[str, Any]:
        goals = self._goals.list_goals() if self._goals else []
        decisions = self._decisions.get_decisions() if self._decisions else []
        feedback = self._feedback.get_records() if self._feedback else []
        events = self._exec_memory.get_events() if self._exec_memory else []

        total_goals = len(goals)
        active = sum(1 for g in goals if g.lifecycle_state == "active")
        done = sum(1 for g in goals if g.lifecycle_state == "completed")
        failed_count = sum(1 for g in goals if g.lifecycle_state in ("failed", "blocked"))

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

        return {
            "goals": {
                "total": total_goals,
                "active": active,
                "completed": done,
                "failed": failed_count,
            },
            "feedback": {
                "total": total_feedback,
                "successes": success_count,
                "failures": failure_count,
                "failure_rate": round(failure_rate, 1),
            },
            "failure_patterns": [{"error": err, "count": cnt} for err, cnt in sorted_patterns],
            "total_execution_events": len(events),
        }

    def _record_impacts(self, goal_id: str, goal_text: str) -> None:
        events = self._exec_memory.get_events() if self._exec_memory else []
        goal_events = [e for e in events if e.get("goal_id") == goal_id]
        seen_paths: set = set()
        for ev in goal_events:
            tool = ev.get("tool", "")
            args = ev.get("args", {}) or {}
            path: str | None = None
            action: str = "affected"
            if tool == "write_file":
                path = args.get("filename")
                action = "wrote"
            elif tool == "read_file":
                path = args.get("filename")
                action = "read"
            elif tool == "list_dir" and args.get("path"):
                path = args.get("path")
                action = "listed"
            if path and path not in seen_paths:
                seen_paths.add(path)
                component = None
                if self._component_registry and self._catalog:
                    from core.structure.project_catalog import FileRecord
                    fake = FileRecord(
                        path=path, dir_path="",
                        extension="", size=0, modified_at="",
                    )
                    component = self._component_registry.assign(fake)
                self._impact_tracker.record_impact(
                    goal_id=goal_id,
                    goal_description=goal_text[:120],
                    file_path=path,
                    component=component,
                    action=action,
                )

    def _record_changes(self, goal_id: str, goal_text: str) -> None:
        events = self._exec_memory.get_events() if self._exec_memory else []
        goal_events = [e for e in events if e.get("goal_id") == goal_id]
        seen_paths: set = set()
        for ev in goal_events:
            tool = ev.get("tool", "")
            args = ev.get("args", {}) or {}
            path: str | None = None
            action_type = "modified"
            if tool == "write_file":
                path = args.get("filename")
            elif tool == "read_file":
                path = args.get("filename")
                action_type = "read"
            elif tool == "list_dir" and args.get("path"):
                path = args.get("path")
                action_type = "listed"
            if path and path not in seen_paths:
                seen_paths.add(path)
                component = None
                if self._component_registry and self._catalog:
                    fake = FileRecord(
                        path=path, dir_path="",
                        extension="", size=0, modified_at="",
                    )
                    component = self._component_registry.assign(fake)
                self._change_store.record_change(
                    goal_id=goal_id,
                    goal_description=goal_text[:120],
                    file_path=path,
                    component=component,
                    action_type=action_type,
                    tool=tool,
                )

    def _record_relationships(self, goal_id: str, goal_text: str) -> None:
        events = self._exec_memory.get_events() if self._exec_memory else []
        goal_events = [e for e in events if e.get("goal_id") == goal_id]
        artifacts: set = set()
        components: set = set()
        for ev in goal_events:
            tool = ev.get("tool", "")
            args = ev.get("args", {}) or {}
            path: str | None = None
            if tool == "write_file":
                path = args.get("filename")
            elif tool == "read_file":
                path = args.get("filename")
            elif tool == "list_dir" and args.get("path"):
                path = args.get("path")
            if path:
                artifacts.add(path)
                if self._component_registry and self._catalog:
                    fake = FileRecord(
                        path=path, dir_path="",
                        extension="", size=0, modified_at="",
                    )
                    comp = self._component_registry.assign(fake)
                    if comp:
                        components.add(comp)
        if artifacts or components:
            self._relationship_store.record_relationship(
                goal_id=goal_id,
                goal_description=goal_text[:120],
                artifacts=list(artifacts),
                components=list(components),
            )

    def route_command(self, request: str) -> Dict[str, Any]:
        intent = self._router.route(request)
        return intent.to_dict()

    def execute_command(self, request: str) -> Dict[str, Any]:
        intent = self._router.route(request)
        cmd = intent.command

        if cmd == "create_file":
            path = intent.parameters.get("filename", "untitled")
            return self.file_create(path, "")
        elif cmd == "create_folder":
            path = intent.parameters.get("filename", "new_folder")
            if self._os_context:
                try:
                    self._os_context.gateway.create(path, "", context="auto")
                    return {"status": "success", "command": cmd, "path": path}
                except Exception as e:
                    return {"status": "error", "command": cmd, "error": str(e)}
            return {"status": "error", "command": cmd, "error": "OS context not initialized"}
        elif cmd == "read_file":
            path = intent.parameters.get("filename", "")
            if not path:
                return {"status": "error", "command": cmd, "error": "no filename specified"}
            return self.file_read(path)
        elif cmd == "update_file":
            path = intent.parameters.get("filename", "")
            if not path:
                return {"status": "error", "command": cmd, "error": "no filename specified"}
            return self.file_create(path, "", context="auto")
        elif cmd == "delete_file":
            path = intent.parameters.get("filename", "")
            if not path:
                return {"status": "error", "command": cmd, "error": "no filename specified"}
            if self._os_context:
                try:
                    self._os_context.gateway.delete(path, context="auto")
                    return {"status": "success", "command": cmd, "path": path}
                except Exception as e:
                    return {"status": "error", "command": cmd, "error": str(e)}
            return {"status": "error", "command": cmd, "error": "OS context not initialized"}
        elif cmd == "list_workspace":
            return self.file_list(".")
        elif cmd == "show_overview":
            return self.context.get_lens("overview")
        elif cmd == "show_structure":
            return self.context.get_lens("structure")
        elif cmd == "show_relationships":
            return self.context.get_lens("relationships")
        elif cmd == "show_workspace":
            return self.get_workspace_activity()
        elif cmd == "generate_handoff":
            return self.get_handoff()
        elif cmd == "create_workspace":
            name = intent.parameters.get("name", "untitled")
            return self.create_workspace(name)
        elif cmd == "switch_workspace":
            name = intent.parameters.get("name", "")
            if not name:
                return {"status": "error", "command": cmd, "error": "no workspace name specified"}
            return self.switch_workspace(name)
        elif cmd == "show_workspaces":
            workspaces = self.list_workspaces()
            return {"status": "success", "command": cmd, "workspaces": workspaces}
        elif cmd == "current_workspace":
            return self.get_current_workspace()
        elif cmd == "execute_goal":
            output = self.process(intent.parameters.get("goal_text", request))
            return output.to_dict()
        else:
            output = self.process(request)
            return output.to_dict()

    def get_debug(self, source: str) -> List[Dict[str, Any]]:
        if source == "events":
            return self._exec_memory.get_events() if self._exec_memory else []
        if source == "decisions":
            return [d.to_dict() for d in self._decisions.get_decisions()] if self._decisions else []
        if source == "feedback":
            return [r.to_dict() for r in self._feedback.get_records()] if self._feedback else []
        return []
