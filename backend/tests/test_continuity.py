from __future__ import annotations

from core.memory.continuity import ContinuityDetector, ContinuationResult, _jaccard_similarity
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackRecord, FeedbackStore
from core.memory.goal_registry import GoalRegistry


class TestJaccardSimilarity:
    def test_identical_texts(self) -> None:
        assert _jaccard_similarity("hello world", "hello world") == 1.0

    def test_no_common_words(self) -> None:
        assert _jaccard_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self) -> None:
        sim = _jaccard_similarity("fix project structure", "fix the project")
        assert 0.3 < sim < 1.0

    def test_case_insensitive(self) -> None:
        assert _jaccard_similarity("Hello World", "hello world") == 1.0

    def test_empty_inputs(self) -> None:
        assert _jaccard_similarity("", "hello") == 0.0
        assert _jaccard_similarity("hello", "") == 0.0
        assert _jaccard_similarity("", "") == 0.0


class TestContinuityDetection:
    def test_no_previous_goals_returns_no_continuation(self) -> None:
        goals = GoalRegistry()
        detector = ContinuityDetector(goal_registry=goals)
        result = detector.detect("write_file /tmp/test.txt with hello")
        assert not result.is_continuation
        assert result.parent_goal_id is None

    def test_matches_failed_goal(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal(description="fix project structure")
        goals.update_state(g.goal_id, "failed")
        detector = ContinuityDetector(goal_registry=goals)
        result = detector.detect("fix project structure")
        assert result.is_continuation
        assert result.parent_goal_id == g.goal_id
        assert "not complete" in (result.continuation_reason or "").lower()

    def test_matches_blocked_goal(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal(description="read config file")
        goals.update_state(g.goal_id, "blocked")
        detector = ContinuityDetector(goal_registry=goals)
        result = detector.detect("read config file again")
        assert result.is_continuation
        assert result.parent_goal_id == g.goal_id

    def test_completed_goal_not_matched(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal(description="simple task")
        goals.update_state(g.goal_id, "completed")
        detector = ContinuityDetector(goal_registry=goals)
        result = detector.detect("simple task")
        assert not result.is_continuation

    def test_low_similarity_not_continuation(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal(description="read config file")
        goals.update_state(g.goal_id, "failed")
        detector = ContinuityDetector(goal_registry=goals)
        result = detector.detect("completely different thing")
        assert not result.is_continuation

    def test_matches_from_feedback(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(
            goal_id="g_abc", action="process data file", outcome="failed",
        ))
        goals = GoalRegistry()
        detector = ContinuityDetector(goal_registry=goals, feedback_store=fb)
        result = detector.detect("process data file")
        assert result.is_continuation

    def test_empty_goal_returns_no_continuation(self) -> None:
        detector = ContinuityDetector()
        result = detector.detect("")
        assert not result.is_continuation

    def test_determinism(self) -> None:
        goals = GoalRegistry()
        g = goals.create_goal(description="test task")
        goals.update_state(g.goal_id, "failed")
        detector = ContinuityDetector(goal_registry=goals)
        result1 = detector.detect("test task")
        result2 = detector.detect("test task")
        assert result1.is_continuation == result2.is_continuation
        assert result1.parent_goal_id == result2.parent_goal_id
        assert result1.continuation_reason == result2.continuation_reason

    def test_to_dict_format(self) -> None:
        result = ContinuationResult(
            is_continuation=True,
            parent_goal_id="g1",
            parent_description="test",
            continuation_reason="reason",
            candidate_goal_ids=("g1",),
        )
        d = result.to_dict()
        assert d["is_continuation"] is True
        assert d["parent_goal_id"] == "g1"
        assert d["parent_description"] == "test"
        assert d["continuation_reason"] == "reason"
        assert d["candidate_goal_ids"] == ["g1"]


class TestContinuationResult:
    def test_defaults_to_no_continuation(self) -> None:
        r = ContinuationResult()
        assert not r.is_continuation
        assert r.parent_goal_id is None
        assert r.parent_description is None
        assert r.continuation_reason is None
        assert r.candidate_goal_ids == ()
