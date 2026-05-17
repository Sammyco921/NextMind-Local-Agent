import json
from core.llm import call_llm


CRITIC_PROMPT = """
You are the Critic in an AI agent system.

Your job is to evaluate execution results against the original step.

Rules:
- Be strict and objective
- Detect incomplete or incorrect outputs
- Suggest fixes when needed
- Do NOT execute tasks yourself
- Keep responses concise
- Return ONLY valid JSON

Required JSON format:

{
  "status": "pass | fail",
  "reason": "...",
  "fix_suggestion": "..."
}
"""


class Critic:
    """
    Evaluates executor output against the intended task step.
    """

    def __init__(self):
        pass

    def evaluate(self, step: str, execution_result: dict) -> dict:
        """
        Evaluate whether a step was completed successfully.

        Args:
            step (str): Original planned step
            execution_result (dict): Output from executor

        Returns:
            dict: Critic evaluation result
        """

        prompt = f"""
{CRITIC_PROMPT}

Original Step:
{step}

Execution Result:
{json.dumps(execution_result, indent=2)}

Evaluate the execution result.
"""

        try:
            response = call_llm(prompt)

            parsed = json.loads(response)

            return {
                "status": parsed.get("status", "fail"),
                "reason": parsed.get("reason", "No reason provided."),
                "fix_suggestion": parsed.get(
                    "fix_suggestion",
                    "No fix suggestion provided."
                )
            }

        except json.JSONDecodeError:
            return {
                "status": "fail",
                "reason": "Critic returned invalid JSON.",
                "fix_suggestion": "Retry evaluation with stricter formatting."
            }

        except Exception as e:
            return {
                "status": "fail",
                "reason": f"Critic system error: {str(e)}",
                "fix_suggestion": "Check LLM connection or prompt formatting."
            }
