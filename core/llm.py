import re
import json
import requests


# ====================================================
# JSON EXTRACTION LAYER (ROBUST)
# ====================================================

def _extract_json(text: str) -> str:
    """
    Extract JSON from messy LLM outputs.

    Handles:
    - ```json blocks
    - ``` generic blocks
    - embedded explanations
    - partial JSON fallback
    """

    if not text:
        raise ValueError("Empty LLM response")

    text = text.strip()

    # -----------------------------
    # Case 1: ```json ... ```
    # -----------------------------
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # -----------------------------
    # Case 2: ``` ... ```
    # -----------------------------
    match = re.search(r"```(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # -----------------------------
    # Case 3: best-effort JSON block
    # (take last valid-looking object)
    # -----------------------------
    candidates = re.findall(r"\{.*?\}", text, re.DOTALL)
    if candidates:
        return candidates[-1].strip()

    return text


# ====================================================
# MAIN LLM CALL (OLLAMA)
# ====================================================

def call_llm(prompt: str) -> str:
    """
    Calls local Ollama model and returns CLEAN JSON string.
    """

    raw_output = _raw_llm_call(prompt)

    cleaned = _extract_json(raw_output)

    # -----------------------------
    # HARD VALIDATION CHECK
    # -----------------------------
    try:
        json.loads(cleaned)
    except Exception as e:
        raise ValueError(
            "LLM did not return valid JSON after cleanup.\n"
            f"Error: {str(e)}\n\nRAW OUTPUT:\n{raw_output}"
        )

    return cleaned


# ====================================================
# OLLAMA BACKEND
# ====================================================

def _raw_llm_call(prompt: str) -> str:

    try:

        response = requests.post(

            "http://localhost:11434/api/chat",

            json={

                "model": "llama3.2:latest",

                "messages": [

                    {"role": "system", "content": "Return ONLY valid JSON."},

                    {"role": "user", "content": prompt}

                ],

                "stream": False

            },

            timeout=60

        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"]

    except Exception as e:

        raise RuntimeError(f"Ollama request failed: {str(e)}")
