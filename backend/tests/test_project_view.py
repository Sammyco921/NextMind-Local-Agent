from __future__ import annotations

from core.memory.decision_store import Decision, DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackRecord, FeedbackStore
from core.memory.goal_registry import GoalRegistry
from core.memory.project_view import ProjectIntelligenceView


class TestProjectViewOverview:
    def test_empty_view(self) -> None:
        view = ProjectIntelligenceView()
        result = view.overview()
        assert result["lens"] == "overview"
        assert result["active_goals"] == []
        assert result["blocked_goals"] == []
        assert result["completed_goals"] == []
        assert result["goal_count"]["total"] == 0

    def test_active_goals_appear(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal("setup project structure")
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.overview()
        assert len(result["active_goals"]) == 1
        assert result["active_goals"][0]["description"] == "setup project structure"
        assert result["goal_count"]["active"] == 1

    def test_blocked_goals_appear(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal("read config file")
        goals.update_state(g.goal_id, "blocked")
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.overview()
        assert len(result["blocked_goals"]) == 1
        assert result["blocked_goals"][0]["goal_id"] == g.goal_id

    def test_completed_goals_appear(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal("write test file")
        goals.update_state(g.goal_id, "completed")
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.overview()
        assert len(result["completed_goals"]) == 1

    def test_continuation_links_from_parent_id(self) -> None:
        goals = GoalRegistry()
        parent = goals.create_goal("fix project")
        child = goals.create_goal("fix tests", parent_id=parent.goal_id)
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.overview()
        assert len(result["continuation_links"]) == 1
        assert result["continuation_links"][0]["child_goal_id"] == child.goal_id
        assert result["continuation_links"][0]["parent_goal_id"] == parent.goal_id

    def test_recurring_failures_from_feedback(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="failed", reason_code="permission denied"))
        fb.append_record(FeedbackRecord(goal_id="g2", action="write", outcome="failed", reason_code="permission denied"))
        fb.append_record(FeedbackRecord(goal_id="g1", action="read", outcome="success"))
        view = ProjectIntelligenceView(feedback_store=fb)
        result = view.overview()
        assert len(result["recurring_failures"]) == 1
        assert result["recurring_failures"][0]["error"] == "permission denied"
        assert result["recurring_failures"][0]["count"] == 2

    def test_recurring_failures_from_action_without_reason(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write data", outcome="failed"))
        fb.append_record(FeedbackRecord(goal_id="g2", action="write data", outcome="failed"))
        view = ProjectIntelligenceView(feedback_store=fb)
        result = view.overview()
        assert len(result["recurring_failures"]) == 1
        assert result["recurring_failures"][0]["error"] == "write data"
        assert result["recurring_failures"][0]["count"] == 2

    def test_no_recurring_failure_below_threshold(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="failed", reason_code="permission denied"))
        view = ProjectIntelligenceView(feedback_store=fb)
        result = view.overview()
        assert len(result["recurring_failures"]) == 0

    def test_goal_counts_accuracy(self) -> None:
        goals = GoalRegistry()
        g1 = goals.create_goal("active work")
        g2 = goals.create_goal("blocked work")
        g3 = goals.create_goal("completed work")
        goals.update_state(g2.goal_id, "blocked")
        goals.update_state(g3.goal_id, "completed")
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.overview()
        assert result["goal_count"]["active"] == 1
        assert result["goal_count"]["blocked"] == 1
        assert result["goal_count"]["completed"] == 1
        assert result["goal_count"]["total"] == 3


class TestProjectViewHistory:
    def test_empty_history(self) -> None:
        view = ProjectIntelligenceView()
        result = view.history()
        assert result["lens"] == "history"
        assert result["entries"] == []

    def test_execution_events_appear(self) -> None:
        store = ExecutionMemoryStore(jsonl_path="/dev/null")
        store.append_event({"goal_id": "g1", "tool": "read_file", "status": "success", "timestamp": "2025-01-01T00:00:00"})
        view = ProjectIntelligenceView(execution_store=store)
        result = view.history()
        assert len(result["entries"]) == 1
        assert result["entries"][0]["type"] == "execution"

    def test_decisions_appear(self) -> None:
        ds = DecisionStore(jsonl_path="/dev/null")
        ds.append_decision(Decision(goal_id="g1", description="decided to read", decision_type="planning", timestamp="2025-01-01T00:00:00"))
        view = ProjectIntelligenceView(decision_store=ds)
        result = view.history()
        assert len(result["entries"]) == 1
        assert result["entries"][0]["type"] == "decision"

    def test_feedback_appears(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="failed", timestamp="2025-01-01T00:00:00"))
        view = ProjectIntelligenceView(feedback_store=fb)
        result = view.history()
        assert len(result["entries"]) == 1
        assert result["entries"][0]["type"] == "feedback"

    def test_entries_chronologically_sorted(self) -> None:
        ds = DecisionStore(jsonl_path="/dev/null")
        ds.append_decision(Decision(goal_id="g1", description="first", decision_type="planning", timestamp="2025-01-01T00:00:01"))
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="success", timestamp="2025-01-01T00:00:00"))
        view = ProjectIntelligenceView(decision_store=ds, feedback_store=fb)
        result = view.history()
        assert len(result["entries"]) == 2
        assert result["entries"][0]["type"] == "feedback"  # earlier
        assert result["entries"][1]["type"] == "decision"   # later

    def test_mixed_sources_combined(self) -> None:
        store = ExecutionMemoryStore(jsonl_path="/dev/null")
        store.append_event({"goal_id": "g1", "tool": "list_dir", "status": "success", "timestamp": "2025-01-01T00:00:00"})
        ds = DecisionStore(jsonl_path="/dev/null")
        ds.append_decision(Decision(goal_id="g1", description="pick tool", decision_type="planning", timestamp="2025-01-01T00:00:01"))
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="list_dir", outcome="success", timestamp="2025-01-01T00:00:02"))
        view = ProjectIntelligenceView(execution_store=store, decision_store=ds, feedback_store=fb)
        result = view.history()
        types = [e["type"] for e in result["entries"]]
        assert types == ["execution", "decision", "feedback"]


class TestProjectViewContinuity:
    def test_empty_continuity(self) -> None:
        view = ProjectIntelligenceView()
        result = view.continuity()
        assert result["lens"] == "continuity"
        assert result["goal_chains"] == []
        assert result["repeated_attempts"] == []

    def test_goal_chains_from_parent_links(self) -> None:
        goals = GoalRegistry()
        parent = goals.create_goal("parent task")
        child = goals.create_goal("child task", parent_id=parent.goal_id)
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.continuity()
        assert len(result["goal_chains"]) == 1
        chain = result["goal_chains"][0]
        assert chain["root"]["goal_id"] == parent.goal_id
        assert len(chain["children"]) == 1
        assert chain["children"][0]["goal_id"] == child.goal_id

    def test_chain_includes_status(self) -> None:
        goals = GoalRegistry()
        parent = goals.create_goal("parent")
        goals.create_goal("child", parent_id=parent.goal_id)
        view = ProjectIntelligenceView(goal_registry=goals)
        result = view.continuity()
        chain = result["goal_chains"][0]
        assert "status" in chain["root"]
        assert "status" in chain["children"][0]

    def test_repeated_attempts_detected(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write data", outcome="failed"))
        fb.append_record(FeedbackRecord(goal_id="g1", action="write data", outcome="failed"))
        fb.append_record(FeedbackRecord(goal_id="g1", action="write data", outcome="success"))
        view = ProjectIntelligenceView(feedback_store=fb)
        result = view.continuity()
        assert len(result["repeated_attempts"]) == 1
        assert result["repeated_attempts"][0]["attempt_count"] == 3

    def test_single_attempt_not_repeated(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write data", outcome="success"))
        view = ProjectIntelligenceView(feedback_store=fb)
        result = view.continuity()
        assert len(result["repeated_attempts"]) == 0


class TestProjectViewDeterminism:
    def test_identical_inputs_identical_overview(self) -> None:
        goals = GoalRegistry()
        goals.create_goal("test task")
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="failed", reason_code="error"))
        view = ProjectIntelligenceView(goal_registry=goals, feedback_store=fb)
        a = view.overview()
        b = view.overview()
        assert a == b

    def test_identical_inputs_identical_history(self) -> None:
        store = ExecutionMemoryStore(jsonl_path="/dev/null")
        store.append_event({"goal_id": "g1", "tool": "read", "status": "success", "timestamp": "2025-01-01T00:00:00"})
        view = ProjectIntelligenceView(execution_store=store)
        a = view.history()
        b = view.history()
        assert a == b

    def test_identical_inputs_identical_continuity(self) -> None:
        goals = GoalRegistry()
        goals.create_goal("root")
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="failed"))
        fb.append_record(FeedbackRecord(goal_id="g1", action="write", outcome="failed"))
        view = ProjectIntelligenceView(goal_registry=goals, feedback_store=fb)
        a = view.continuity()
        b = view.continuity()
        assert a == b

    def test_with_no_stores_all_lenses_return_empty(self) -> None:
        view = ProjectIntelligenceView()
        assert view.overview()["active_goals"] == []
        assert view.history()["entries"] == []
        assert view.continuity()["goal_chains"] == []


class TestProjectViewIsolation:
    def test_no_mutation_of_goal_registry(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal("test")
        orig = g.to_dict()
        view = ProjectIntelligenceView(goal_registry=goals)
        view.overview()
        view.history()
        view.continuity()
        assert g.to_dict() == orig
        assert goals.get_goal(g.goal_id).to_dict() == orig

    def test_no_mutation_of_feedback_store(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="failed"))
        count_before = len(fb.get_records())
        view = ProjectIntelligenceView(feedback_store=fb)
        view.overview()
        view.history()
        view.continuity()
        assert len(fb.get_records()) == count_before

    def test_no_mutation_of_decision_store(self) -> None:
        ds = DecisionStore(jsonl_path="/dev/null")
        ds.append_decision(Decision(goal_id="g1", description="test", decision_type="planning", timestamp="2025-01-01T00:00:00"))
        count_before = len(ds.get_decisions())
        view = ProjectIntelligenceView(decision_store=ds)
        view.overview()
        view.history()
        view.continuity()
        assert len(ds.get_decisions()) == count_before

    def test_no_mutation_of_execution_store(self) -> None:
        store = ExecutionMemoryStore(jsonl_path="/dev/null")
        store.append_event({"goal_id": "g1", "tool": "read", "status": "success", "timestamp": "2025-01-01T00:00:00"})
        count_before = len(store.get_events())
        view = ProjectIntelligenceView(execution_store=store)
        view.overview()
        view.history()
        view.continuity()
        assert len(store.get_events()) == count_before
