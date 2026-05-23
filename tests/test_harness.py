from typing import Dict, Any, List

from tools.tool_registry import ToolRegistry
from core.validator import Validator
from core.orchestrator import Orchestrator


class TestHarness:
    """
    v0.9 Contract Test Harness

    Purpose:
    - Validate system correctness under deterministic + adversarial inputs
    - Ensure contract compliance across all layers

    Non-goals:
    - No UI
    - No fuzzing randomness
    - No ML evaluation
    """

    def __init__(self, registry: ToolRegistry, planner):
        self.registry = registry
        self.planner = planner
        self.validator = Validator(registry)
        self.orchestrator = Orchestrator(planner, registry, self.validator)

        self.results: List[Dict[str, Any]] = []

    # =====================================================
    # RUN SINGLE TEST
    # =====================================================

    def run_test(self, name: str, goal: str, expect_status: str) -> Dict[str, Any]:

        result = self.orchestrator.run(goal)

        passed = result.get("status") == expect_status

        test_result = {
            "test_name": name,
            "input": goal,
            "expected_status": expect_status,
            "actual_status": result.get("status"),
            "passed": passed,
            "details": result
        }

        self.results.append(test_result)

        return test_result

    # =====================================================
    # RUN TEST SUITE
    # =====================================================

    def run_suite(self, tests: List[Dict[str, str]]) -> Dict[str, Any]:

        summary = {
            "total": len(tests),
            "passed": 0,
            "failed": 0,
            "results": []
        }

        for t in tests:
            result = self.run_test(
                name=t["name"],
                goal=t["goal"],
                expect_status=t["expect_status"]
            )

            summary["results"].append(result)

            if result["passed"]:
                summary["passed"] += 1
            else:
                summary["failed"] += 1

        summary["success_rate"] = (
            summary["passed"] / summary["total"] if summary["total"] > 0 else 0
        )

        return summary

    # =====================================================
    # PREDEFINED V0.9 CONTRACT TESTS
    # =====================================================

    def default_contract_tests(self) -> List[Dict[str, str]]:

        return [
            # ---------------------------------------------
            # VALID MULTI STEP EXECUTION
            # ---------------------------------------------
            {
                "name": "multi_step_file_ops",
                "goal": 'Create a.txt with "A", then create b.txt with "B", then read a.txt, then list directory',
                "expect_status": "success"
            },

            # ---------------------------------------------
            # MISSING FILE HANDLING
            # ---------------------------------------------
            {
                "name": "missing_file_should_fail_cleanly",
                "goal": "Read definitely_missing_file.txt",
                "expect_status": "fail"
            },

            # ---------------------------------------------
            # INVALID INPUT (ADVERSARIAL)
            # ---------------------------------------------
            {
                "name": "garbage_input_rejection",
                "goal": "?!@#$%^&*()_+ random nonsense input",
                "expect_status": "fail"
            },

            # ---------------------------------------------
            # MALFORMED TOOL ATTEMPT
            # ---------------------------------------------
            {
                "name": "malformed_tool_input",
                "goal": '{"tool": "write_file", "args": "not a dict"}',
                "expect_status": "fail"
            },

            # ---------------------------------------------
            # COMPLEX SEQUENCE
            # ---------------------------------------------
            {
                "name": "multi_file_pipeline",
                "goal": "Create log1.txt with alpha, then create log2.txt with beta, then read log1.txt, then list directory",
                "expect_status": "success"
            }
        ]

    # =====================================================
    # EXECUTION ENTRY
    # =====================================================

    def run_default_suite(self) -> Dict[str, Any]:
        return self.run_suite(self.default_contract_tests())

    # =====================================================
    # REPORTING
    # =====================================================

    def print_summary(self, summary: Dict[str, Any]) -> None:

        print("\n=== NEXTMIND v0.9 TEST HARNESS REPORT ===\n")

        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success Rate: {summary['success_rate']:.2f}")

        print("\n--- Detailed Results ---\n")

        for r in summary["results"]:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"[{status}] {r['test_name']}")
            print(f"  expected: {r['expected_status']}")
            print(f"  actual:   {r['actual_status']}")
            print()