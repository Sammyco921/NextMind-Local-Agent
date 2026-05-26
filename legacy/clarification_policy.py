from typing import Dict, Any, List


class ClarificationPolicy:
    """
    v1 Clarification Policy Engine

    Responsibilities:
    - Decide whether to block, clarify, or proceed
    - Prevent unsafe or underspecified execution
    - Reduce over-blocking (critical v1 improvement)
    """

    # =====================================================
    # ENTRY POINT
    # =====================================================

    def evaluate(self, analysis: Dict[str, Any]) -> Dict[str, Any]:

        status = analysis.get("status")
        risk = analysis.get("risk_level", 0)
        questions = analysis.get("questions", [])

        # -------------------------------------------------
        # HARD BLOCK CONDITIONS
        # -------------------------------------------------

        if risk >= 4:
            return {
                "decision": "block",
                "blocking": True,
                "questions": questions or [
                    "Request is too ambiguous or unsafe to execute"
                ]
            }

        # adversarial / nonsense input
        if status == "blocked":
            return {
                "decision": "block",
                "blocking": True,
                "questions": questions
            }

        # -------------------------------------------------
        # CLARIFICATION CONDITIONS
        # -------------------------------------------------

        # missing required structured parameters
        if status == "unclear" and len(questions) > 0:

            # IMPORTANT FIX:
            # only clarify if ambiguity is structural, not cosmetic

            if self._requires_structural_clarification(questions):
                return {
                    "decision": "clarify",
                    "blocking": False,
                    "questions": questions
                }

        # -------------------------------------------------
        # DEFAULT PROCEED (FIXED BEHAVIOR)
        # -------------------------------------------------

        return {
            "decision": "proceed",
            "blocking": False,
            "questions": []
        }

    # =====================================================
    # HEURISTIC: STRUCTURAL vs COSMETIC AMBIGUITY
    # =====================================================

    def _requires_structural_clarification(self, questions: List[str]) -> bool:

        structural_keywords = [
            "filename",
            "content",
            "what file",
            "which file",
            "exact steps",
            "what should",
            "how should"
        ]

        for q in questions:
            q_lower = q.lower()

            for keyword in structural_keywords:
                if keyword in q_lower:
                    return True

        return False