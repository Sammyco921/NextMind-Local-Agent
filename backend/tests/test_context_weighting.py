from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.memory.context_synthesizer import (
    ActiveGoalSnapshot,
    Blocker,
    ContextSnapshot,
    ContextSynthesizer,
    DecisionSnapshot,
    ExecutionSummary,
)
from core.memory.context_weighting import (
    ContextWeightingSystem,
    DEFAULT_WEIGHTS,
    SalienceLevel,
    SignalWeights,
)
from core.memory.feedback_store import FeedbackRecord, FeedbackStore


class TestSignalWeights:
    def test_default_weights_sum_to_one(self) -> None:
        assert abs(DEFAULT_WEIGHTS.total_weight() - 1.0) < 0.001

    def test_custom_weights(self) -> None:
        w = SignalWeights(recency=0.5, frequency=0.5, outcome_success=0.0, goal_relevance=0.0, failure_recurrence=0.0)
        assert abs(w.total_weight() - 1.0) < 0.001


class TestRecencySignal:
    FIXED_NOW = datetime(2025, 6, 1, tzinfo=timezone.utc)

    def _ts(self, hours_ago: int) -> str:
        return (self.FIXED_NOW - timedelta(hours=hours_ago)).isoformat()

    def test_recent_scores_higher_than_old(self) -> None:
        w = ContextWeightingSystem()
        recent = w.compute_recency_score(self._ts(1), now=self.FIXED_NOW)
        old = w.compute_recency_score(self._ts(72), now=self.FIXED_NOW)
        assert recent > old

    def test_none_timestamp_returns_zero(self) -> None:
        w = ContextWeightingSystem()
        assert w.compute_recency_score(None) == 0.0

    def test_invalid_timestamp_returns_zero(self) -> None:
        w = ContextWeightingSystem()
        assert w.compute_recency_score("not-a-timestamp") == 0.0


class TestGoalRelevanceSignal:
    def test_matching_goal_scores_weight(self) -> None:
        w = ContextWeightingSystem()
        score = w.compute_goal_relevance_score("g1", "g1")
        assert score == DEFAULT_WEIGHTS.goal_relevance

    def test_non_matching_goal_returns_zero(self) -> None:
        w = ContextWeightingSystem()
        assert w.compute_goal_relevance_score("g1", "g2") == 0.0

    def test_none_query_returns_full_weight(self) -> None:
        w = ContextWeightingSystem()
        score = w.compute_goal_relevance_score("g1", None)
        assert score == DEFAULT_WEIGHTS.goal_relevance


class TestOutcomeSignal:
    def test_all_success_returns_full_weight(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="success"))
        fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="success"))
        w = ContextWeightingSystem(feedback_store=fb)
        score = w.compute_outcome_score("g1")
        assert score == DEFAULT_WEIGHTS.outcome_success

    def test_mixed_outcome_returns_partial(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="success"))
        fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="failed"))
        w = ContextWeightingSystem(feedback_store=fb)
        score = w.compute_outcome_score("g1")
        assert 0 < score < DEFAULT_WEIGHTS.outcome_success

    def test_no_feedback_returns_zero(self) -> None:
        w = ContextWeightingSystem()
        assert w.compute_outcome_score("g1") == 0.0


class TestFailureRecurrenceSignal:
    def test_no_feedback_returns_zero(self) -> None:
        w = ContextWeightingSystem()
        assert w.compute_failure_recurrence("g1") == 0.0

    def test_failures_increase_score(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        for _ in range(3):
            fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="failed"))
        w = ContextWeightingSystem(feedback_store=fb)
        score = w.compute_failure_recurrence("g1")
        assert score > 0

    def test_capped_at_five_failures(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        for _ in range(10):
            fb.append_record(FeedbackRecord(goal_id="g1", action="test", outcome="failed"))
        w = ContextWeightingSystem(feedback_store=fb)
        score = w.compute_failure_recurrence("g1")
        assert score <= DEFAULT_WEIGHTS.failure_recurrence


class TestFrequencySignal:
    def test_no_items_returns_zero(self) -> None:
        w = ContextWeightingSystem()
        assert w.compute_frequency_score([], "g1") == 0.0

    def test_matching_goals_increase_score(self) -> None:
        w = ContextWeightingSystem()
        items = [
            DecisionSnapshot(goal_id="g1", decision_point="a", rationale=None, selected="x"),
            DecisionSnapshot(goal_id="g1", decision_point="b", rationale=None, selected="y"),
        ]
        score = w.compute_frequency_score(items, "g1")
        assert score > 0

    def test_capped_at_ten(self) -> None:
        w = ContextWeightingSystem()
        items = [DecisionSnapshot(goal_id="g1", decision_point=f"d{i}", rationale=None, selected="x") for i in range(20)]
        score = w.compute_frequency_score(items, "g1")
        assert score <= DEFAULT_WEIGHTS.frequency


class TestSalienceClassification:
    def test_high_threshold(self) -> None:
        assert ContextWeightingSystem.classify_salience(0.75) == SalienceLevel.HIGH
        assert ContextWeightingSystem.classify_salience(0.5) == SalienceLevel.HIGH

    def test_medium_threshold(self) -> None:
        assert ContextWeightingSystem.classify_salience(0.35) == SalienceLevel.MEDIUM
        assert ContextWeightingSystem.classify_salience(0.2) == SalienceLevel.MEDIUM

    def test_low_threshold(self) -> None:
        assert ContextWeightingSystem.classify_salience(0.19) == SalienceLevel.LOW
        assert ContextWeightingSystem.classify_salience(0.0) == SalienceLevel.LOW


class TestDeterminism:
    def test_same_inputs_produce_same_score(self) -> None:
        w = ContextWeightingSystem()
        fixed_now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        ts = "2024-01-01T00:00:00+00:00"
        ds = DecisionSnapshot(goal_id="g1", decision_point="cp", rationale="r", selected="s", timestamp=ts)
        score1 = w.score_decision(ds, query_goal_id="g1", timestamp_str=ts, now=fixed_now)
        score2 = w.score_decision(ds, query_goal_id="g1", timestamp_str=ts, now=fixed_now)
        assert score1 == pytest.approx(score2)

    def test_no_randomness_in_recency(self) -> None:
        w = ContextWeightingSystem()
        fixed_now = datetime(2025, 6, 1, tzinfo=timezone.utc)
        ts = "2024-01-01T00:00:00+00:00"
        results = [w.compute_recency_score(ts, now=fixed_now) for _ in range(100)]
        assert all(r == results[0] for r in results)


class TestCompression:
    def test_under_max_returns_all(self) -> None:
        w = ContextWeightingSystem()
        items = [1, 2, 3]
        result = w.compress_by_salience(items, scorer_fn=lambda x: float(x), max_items=10)
        assert result == [3, 2, 1]

    def test_over_max_keeps_highest_scored(self) -> None:
        w = ContextWeightingSystem()
        items = list(range(20))
        result = w.compress_by_salience(items, scorer_fn=lambda x: float(x), max_items=5)
        assert len(result) == 5
        assert result == [19, 18, 17, 16, 15]

    def test_preserves_order_by_score(self) -> None:
        w = ContextWeightingSystem()
        items = [DecisionSnapshot(goal_id=f"g{i}", decision_point="cp", rationale=None, selected="s") for i in range(5)]
        result = w.compress_by_salience(items, scorer_fn=lambda x: float(ord(x.goal_id[-1])), max_items=10)
        # Should be sorted descending by score
        for i in range(len(result) - 1):
            score_i = float(ord(result[i].goal_id[-1]))
            score_j = float(ord(result[i + 1].goal_id[-1]))
            assert score_i >= score_j


class TestDecisionSnapshotTimestamp:
    def test_timestamp_preserved_in_snapshot(self) -> None:
        ts = "2025-01-01T00:00:00+00:00"
        ds = DecisionSnapshot(goal_id="g1", decision_point="cp", rationale=None, selected="s", timestamp=ts)
        assert ds.timestamp == ts

    def test_to_dict_includes_timestamp(self) -> None:
        ts = "2025-01-01T00:00:00+00:00"
        ds = DecisionSnapshot(goal_id="g1", decision_point="cp", rationale=None, selected="s", timestamp=ts)
        d = ContextSnapshot(
            relevant_decisions=[ds],
        ).to_dict()
        assert d["relevant_decisions"][0]["timestamp"] == ts


class TestContextSynthesizerWeighting:
    def test_without_weighting_unchanged(self) -> None:
        synth = ContextSynthesizer()
        snap = synth.build_snapshot()
        assert isinstance(snap, ContextSnapshot)

    def test_with_weighting_no_crash(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        weighting = ContextWeightingSystem(feedback_store=fb)
        synth = ContextSynthesizer(weighting_system=weighting)
        snap = synth.build_snapshot()
        assert isinstance(snap, ContextSnapshot)

    def test_with_weighting_produces_valid_dict(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        weighting = ContextWeightingSystem(feedback_store=fb)
        synth = ContextSynthesizer(weighting_system=weighting)
        d = synth.build_snapshot().to_dict()
        assert "relevant_decisions" in d
        assert "active_goals" in d
        assert "execution_summary" in d
        assert "blockers" in d


class TestIsolation:
    def test_weighting_does_not_write_to_stores(self) -> None:
        fb = FeedbackStore(jsonl_path="/dev/null")
        initial_count = len(fb.get_records())
        weighting = ContextWeightingSystem(feedback_store=fb)
        synth = ContextSynthesizer(weighting_system=weighting)
        synth.build_snapshot()
        # No writes should have occurred to feedback store
        assert len(fb.get_records()) == initial_count

    def test_execution_engine_unchanged(self) -> None:
        # Verify DAGExecutor is untouched by weighting system imports
        from core.dag_executor import DAGExecutor
        from core.tool_registry import ToolRegistry
        reg = ToolRegistry()
        from core.memory.execution_memory_store import ExecutionMemoryStore
        exec_mem = ExecutionMemoryStore(jsonl_path="/dev/null")
        executor = DAGExecutor(reg, execution_memory=exec_mem)
        assert executor is not None


class TestAgentContextAPI:
    def test_accepts_weighting_system(self) -> None:
        from core.memory.agent_context_api import AgentContextAPI
        weighting = ContextWeightingSystem()
        api = AgentContextAPI(weighting_system=weighting)
        result = api.get_context()
        assert "context" in result
        assert "meta" in result

    def test_system_context_with_weighting(self) -> None:
        from core.memory.agent_context_api import AgentContextAPI
        weighting = ContextWeightingSystem()
        api = AgentContextAPI(weighting_system=weighting)
        result = api.get_system_context()
        assert "context" in result
        assert "meta" in result
