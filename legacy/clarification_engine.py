from typing import Dict, Any, List


class ClarificationEngine:
    """
    v1 Clarification Engine (Intent Repair Layer)

    Responsibilities:
    - Convert analysis → structured clarification needs
    - Generate contextual questions
    - Avoid over-questioning
    """

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def analyze(self, goal: str) -> Dict[str, Any]:

        risk = self._estimate_risk(goal)
        issues = self._detect_ambiguities(goal)

        if risk >= 4:
            return {
                "status": "blocked",
                "blocking": True,
                "risk_level": risk,
                "questions": ["Request contains unsafe or unstructured instructions"]
            }

        if len(issues) == 0:
            return {
                "status": "clear",
                "blocking": False,
                "risk_level": risk,
                "questions": []
            }

        # decide if clarification is actually needed
        if risk <= 2 and self._is_minor_ambiguity(issues):
            return {
                "status": "clear",
                "blocking": False,
                "risk_level": risk,
                "questions": []
            }

        return {
            "status": "unclear",
            "blocking": False,
            "risk_level": risk,
            "questions": self._generate_questions(issues)
        }

    # =====================================================
    # RISK ESTIMATION
    # =====================================================

    def _estimate_risk(self, text: str) -> int:

        text_lower = text.lower()

        risky_keywords = [
            "delete all",
            "remove everything",
            "wipe",
            "system",
            "rm -rf"
        ]

        for k in risky_keywords:
            if k in text_lower:
                return 5

        # adversarial noise detection
        if any(c in text for c in ["?!", "@#", "%%%%"]):
            return 3

        return 1

    # =====================================================
    # AMBIGUITY DETECTION
    # =====================================================

    def _detect_ambiguities(self, text: str) -> List[str]:

        issues = []
        lower = text.lower()

        # missing file target
        if "file" in lower and "txt" not in lower:
            issues.append("missing_filename")

        # missing content spec
        if "create" in lower and "\"" not in text:
            issues.append("missing_content")

        # vague verbs
        vague = ["something", "stuff", "data", "process", "do something"]
        if any(v in lower for v in vague):
            issues.append("vague_instruction")

        # multi-step ambiguity
        if "then" in lower and "and then" in lower:
            issues.append("ambiguous_sequence")

        return issues

    # =====================================================
    # QUESTION GENERATION (KEY IMPROVEMENT)
    # =====================================================

    def _generate_questions(self, issues: List[str]) -> List[str]:

        questions = []

        for issue in issues:

            if issue == "missing_filename":
                questions.append("Which file should be used or created?")

            elif issue == "missing_content":
                questions.append("What content should be written to the file?")

            elif issue == "vague_instruction":
                questions.append("Can you specify exactly what should be done instead of 'something' or 'process'?")

            elif issue == "ambiguous_sequence":
                questions.append("Should the steps be executed strictly in order as written, or can they be optimized?")

        return questions

    # =====================================================
    # SIMPLIFICATION RULE
    # =====================================================

    def _is_minor_ambiguity(self, issues: List[str]) -> bool:
        """
        Minor ambiguity = safe to proceed without interrupting user
        """

        blocking_issues = [
            "missing_filename",
            "missing_content"
        ]

        # if only vague wording exists, it's safe
        return all(i not in blocking_issues for i in issues)