#!/usr/bin/env python3
"""
NextMind — Deterministic DAG Execution Engine
Intent → Normalization → Parsing → DAG → Validation → Execution
"""

from __future__ import annotations

import argparse
import os
import sys

from core.debug_formatter import format_execution_result
from core.execution_mode import ExecutionMode
from core.memory.agent_context_api import AgentContextAPI
from core.memory.agent_loop_controller import AgentLoopController
from core.memory.context_weighting import ContextWeightingSystem
from core.memory.decision_store import DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackStore
from core.memory.goal_registry import GoalRegistry
from core.strict_pipeline import StrictPipeline
from core.tool_registry import ToolRegistry
from core.tool_schemas import TOOL_SCHEMAS

from tools.inject_failure import INJECT_FAILURE_TOOL, inject_failure
from tools.list_dir import list_dir
from tools.read_file import read_file
from tools.write_file import write_file

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_DEMO_GOAL = """
1. create src/alpha.txt with "alpha"
2. create src/beta.txt with "beta"
3. read src/alpha.txt
4. read src/beta.txt
5. create src/result.txt with combined reversed content
6. list files in src directory
""".strip()

_EXEC_MEMORY = ExecutionMemoryStore(jsonl_path=os.path.join(ROOT, "memory", "execution_events.jsonl"))
_GOALS = GoalRegistry()
_DECISIONS = DecisionStore(jsonl_path=os.path.join(ROOT, "memory", "decisions.jsonl"))
_FEEDBACK = FeedbackStore(jsonl_path=os.path.join(ROOT, "memory", "feedback.jsonl"))
_WEIGHTING = ContextWeightingSystem(feedback_store=_FEEDBACK)
_API = AgentContextAPI(execution_store=_EXEC_MEMORY, decision_store=_DECISIONS, goal_registry=_GOALS, weighting_system=_WEIGHTING)
_CONTROLLER = AgentLoopController(api=_API, goal_registry=_GOALS)


def bootstrap_tools(registry: ToolRegistry) -> None:
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    registry.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])
    registry.register(
        INJECT_FAILURE_TOOL, inject_failure, TOOL_SCHEMAS.get(INJECT_FAILURE_TOOL, {}),
    )


def run_pipeline(
    goal: str,
    *,
    debug: bool = False,
    mode: ExecutionMode | None = None,
) -> int:
    registry = ToolRegistry()
    bootstrap_tools(registry)

    pipeline = StrictPipeline(registry, execution_memory=_EXEC_MEMORY, goal_registry=_GOALS, decision_store=_DECISIONS, feedback_store=_FEEDBACK)
    result = pipeline.run(goal, mode=mode)

    if result.status == "clarification_required":
        print("\n--- CLARIFICATION REQUIRED ---")
        print("The intent is not fully specified. Execution cannot proceed.\n")
        if result.clarification:
            req = result.clarification
            print(f"Status: {req.status.value}")
            print(f"Steps detected: {req.step_count}")
            if req.detected_tools:
                print(f"Detected tools: {', '.join(req.detected_tools)}")
            if req.missing_fields:
                print("\nMissing fields:")
                for mf in req.missing_fields:
                    print(f"  - Step {mf.step_index + 1}: {mf.question}")
                    if mf.expected_format:
                        print(f"    Expected format: {mf.expected_format}")
            if req.clarification_questions:
                print("\nSummary:")
                for q in req.clarification_questions:
                    print(f"  ? {q}")
            if req.ambiguity_warnings:
                print("\nWarnings:")
                for w in req.ambiguity_warnings:
                    print(f"  - {w}")
        print("\nPipeline stages:")
        for stage in result.stages:
            print(f"  [{stage.status}] {stage.stage}: {stage.detail}")
        return 2

    if result.status != "success":
        print(f"\n--- FAILED @ {result.failed_stage} ---")
        if result.failure:
            print(f"Reason: {result.failure.reason}")
            for r in result.failure.reasons:
                print(" -", r)
        if result.warnings:
            print("\nWarnings:")
            for w in result.warnings:
                print(" -", w)
        print("\nPipeline stages:")
        for stage in result.stages:
            print(f"  [{stage.status}] {stage.stage}: {stage.detail}")
        return 1

    if result.warnings:
        print("\nWarnings (non-fatal):")
        for w in result.warnings:
            print(" -", w)

    if debug and result.execution:
        print(format_execution_result(
            result.execution,
            goal=goal,
            validation={"status": "valid", "errors": []},
        ))
    else:
        print("\n--- RESULT ---")
        print(result.to_dict())

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="NextMind — Deterministic DAG Execution Engine")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--context", action="store_true", help="Print context snapshot via API and exit")
    parser.add_argument("--context-goal", type=str, default=None, help="Goal ID filter for context snapshot")
    parser.add_argument("--api", action="store_true", help="Print full API response (context + meta) and exit")
    parser.add_argument("--api-goal", type=str, default=None, help="Goal ID for --api")
    parser.add_argument("--goal", type=str, default=None)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--mode", type=str, default=None,
                        choices=[m.value for m in ExecutionMode],
                        help="Execution mode")
    parser.add_argument("--observe", action="store_true", help="Agent loop: observe context")
    parser.add_argument("--interpret", action="store_true", help="Agent loop: interpret context into agent state")
    parser.add_argument("--propose", action="store_true", help="Agent loop: propose next action from agent state")
    parser.add_argument("--execute", action="store_true", help="Agent loop: execute proposed action (requires --allow-execute)")
    parser.add_argument("--allow-execute", action="store_true", help="Enable --execute (safety gate)")
    parser.add_argument("--loop-goal", type=str, default=None, help="Goal ID for agent loop operations")
    args = parser.parse_args()

    mode: ExecutionMode | None = None
    if args.mode:
        mode = ExecutionMode(args.mode)

    if args.observe:
        import json
        goal_ids = [args.loop_goal] if args.loop_goal else None
        result = _CONTROLLER.observe(goal_ids=goal_ids)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.interpret:
        import json
        goal_ids = [args.loop_goal] if args.loop_goal else None
        ctx = _CONTROLLER.observe(goal_ids=goal_ids)
        state = _CONTROLLER.interpret(ctx)
        print(json.dumps(state, indent=2))
        sys.exit(0)

    if args.propose:
        import json
        goal_ids = [args.loop_goal] if args.loop_goal else None
        ctx = _CONTROLLER.observe(goal_ids=goal_ids)
        state = _CONTROLLER.interpret(ctx)
        proposal = _CONTROLLER.propose_next_action(state)
        print(json.dumps(proposal, indent=2))
        sys.exit(0)

    if args.execute:
        if not args.allow_execute:
            print("ERROR: --execute requires --allow-execute for safety")
            sys.exit(1)
        import json
        goal_ids = [args.loop_goal] if args.loop_goal else None
        ctx = _CONTROLLER.observe(goal_ids=goal_ids)
        state = _CONTROLLER.interpret(ctx)
        proposal = _CONTROLLER.propose_next_action(state)
        result = _CONTROLLER.execute(proposal)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.api:
        if args.api_goal:
            result = _API.get_goal_context(args.api_goal)
        else:
            result = _API.get_system_context()
        import json
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.context:
        if args.context_goal:
            result = _API.get_goal_context(args.context_goal)
        else:
            result = _API.get_system_context()
        import json
        print(json.dumps(result["context"], indent=2))
        sys.exit(0)

    print("\n=== NextMind — Deterministic DAG Execution Engine ===\n")

    if args.mode:
        print(f"  [mode] {mode}\n")

    if args.goal or args.demo:
        goal = args.goal if args.goal else DEFAULT_DEMO_GOAL
        print("--- PIPELINE START ---")
        sys.exit(run_pipeline(goal, debug=args.debug, mode=mode))

    while True:
        goal = input("\nEnter goal (or 'exit'): ")
        if goal.strip().lower() == "exit":
            break
        print("\n--- PIPELINE START ---")
        run_pipeline(goal, debug=args.debug, mode=mode)


if __name__ == "__main__":
    main()
