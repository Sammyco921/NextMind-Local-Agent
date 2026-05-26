# core/execution_loop.py
#
# v1.8 self-correcting agent: plan → execute → evaluate → repair (bounded).

from __future__ import annotations

from typing import List, Optional

from core.agent_types import AgentRunResult, EvaluationResult
from core.dag_executor import DAGExecutor
from core.dag_node import DAG
from core.dag_planner import DAGPlanner
from core.dag_validator import DAGValidator
from core.evaluator import Evaluator
from core.planning_errors import PLANNING_ERROR_TOOL
from core.planning_types import PlanResult
from core.repair_planner import RepairPlanner
from core.tool_registry import ToolRegistry

MAX_REPAIR_ITERATIONS = 3


class AgentExecutionLoop:
    """
    Looped deterministic agent compiler:
    hypothesis plan → execute → evaluate → repair → re-execute (max 3 repairs).
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.planner = DAGPlanner(registry=registry)
        self.validator = DAGValidator(registry)
        self.executor = DAGExecutor(registry)
        self.evaluator = Evaluator()
        self.repair_planner = RepairPlanner()

    def run_agent(self, goal: str) -> AgentRunResult:
        plan_result = self.planner.plan_with_result(goal)

        if plan_result.status == "planning_failed":
            return AgentRunResult(
                goal=goal,
                status="planning_failed",
                planning_errors=list(plan_result.errors),
                iterations=0,
            )

        dag = plan_result.dag
        if self._is_planning_error_dag(dag):
            return AgentRunResult(
                goal=goal,
                status="planning_failed",
                planning_errors=[
                    dag.nodes[0].raw_args.get("message", "planning error")
                ],
                iterations=0,
                dag=dag,
            )

        validation = self.validator.validate(dag)
        if validation["status"] != "valid":
            return AgentRunResult(
                goal=goal,
                status="validation_failed",
                planning_errors=validation.get("errors", []),
                iterations=0,
                dag=dag,
            )

        evaluations: List[EvaluationResult] = []
        repair_log: List[str] = []
        execution = None
        iteration = 0

        for iteration in range(1, MAX_REPAIR_ITERATIONS + 1):
            execution = self.executor.execute(dag, goal)
            evaluation = self.evaluator.check(goal, execution, dag)
            evaluations.append(evaluation)

            if evaluation.passed:
                return AgentRunResult(
                    goal=goal,
                    status="success",
                    execution=execution,
                    evaluations=evaluations,
                    iterations=iteration,
                    dag=dag,
                    repair_log=repair_log,
                )

            if iteration >= MAX_REPAIR_ITERATIONS:
                break

            dag_before = len(dag.nodes)
            dag = self.repair_planner.fix(
                dag, execution, evaluation, goal=goal
            )
            repair_log.append(
                f"iteration {iteration}: applied repair after "
                f"{len(evaluation.issues)} issue(s); nodes={dag_before}"
            )

            validation = self.validator.validate(dag)
            if validation["status"] != "valid":
                repair_log.append(
                    f"iteration {iteration}: repaired DAG failed validation"
                )
                return AgentRunResult(
                    goal=goal,
                    status="validation_failed",
                    execution=execution,
                    evaluations=evaluations,
                    iterations=iteration,
                    dag=dag,
                    repair_log=repair_log,
                    planning_errors=validation.get("errors", []),
                )

        return AgentRunResult(
            goal=goal,
            status="repair_exhausted",
            execution=execution,
            evaluations=evaluations,
            iterations=iteration,
            dag=dag,
            repair_log=repair_log,
        )

    @staticmethod
    def _is_planning_error_dag(dag: DAG) -> bool:
        return bool(
            len(dag.nodes) == 1
            and dag.nodes[0].tool_name == PLANNING_ERROR_TOOL
        )


def run_agent(goal: str, registry: ToolRegistry) -> AgentRunResult:
    """Module-level entry for the v1.8 agent loop."""
    return AgentExecutionLoop(registry).run_agent(goal)
