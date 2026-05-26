#!/usr/bin/env python3
"""
NextMind v1.9.1 — Intent → Normalization → Parsing → DAG → Validation → Execution
"""

from __future__ import annotations

import argparse
import os
import sys

from core.debug_formatter import format_execution_result
from core.strict_pipeline import StrictPipeline
from core.tool_registry import ToolRegistry
from core.tool_schemas import TOOL_SCHEMAS

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


def bootstrap_tools(registry: ToolRegistry) -> None:
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    registry.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])


def run_pipeline(goal: str, *, debug: bool = False) -> int:
    registry = ToolRegistry()
    bootstrap_tools(registry)

    result = StrictPipeline(registry).run(goal)

    if result.status != "success":
        print(f"\n--- FAILED @ {result.failed_stage} ---")
        if result.failure:
            print(f"Reason: {result.failure.reason}")
            for r in result.failure.reasons:
                print(" -", r)
            if result.failure.recoverable:
                print("(recoverable)")
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
    parser = argparse.ArgumentParser(description="NextMind v1.9.1")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--goal", type=str, default=None)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    print("\n=== NextMind v1.9.1 ===\n")

    if args.goal or args.demo:
        goal = args.goal if args.goal else DEFAULT_DEMO_GOAL
        print("--- STRICT PIPELINE START ---")
        sys.exit(run_pipeline(goal, debug=args.debug))

    while True:
        goal = input("\nEnter goal (or 'exit'): ")
        if goal.strip().lower() == "exit":
            break
        print("\n--- STRICT PIPELINE START ---")
        run_pipeline(goal, debug=args.debug)


if __name__ == "__main__":
    main()
