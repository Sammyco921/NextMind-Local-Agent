import json
import requests

from config.config import OLLAMA_CONFIG


class LLMError(Exception):
    """
    Custom exception for LLM-related failures.
    """
    pass


def call_llm(prompt: str, system_prompt: str = None) -> str:
    """
    Send a prompt to the local Ollama model and return the response.

    Args:
        prompt (str):
            User/task prompt sent to the model.

        system_prompt (str, optional):
            Optional system instruction layer.

    Returns:
        str:
            Model response text.

    Raises:
        LLMError:
            If request fails or response is malformed.
    """

    url = (
        f"{OLLAMA_CONFIG.BASE_URL}"
        f"{OLLAMA_CONFIG.GENERATE_ENDPOINT}"
    )

    payload = {
        "model": OLLAMA_CONFIG.MODEL,
        "prompt": prompt,
        "stream": OLLAMA_CONFIG.STREAM,
        "options": {
            "temperature": OLLAMA_CONFIG.TEMPERATURE
        }
    }

    # --------------------------------------------------------
    # Optional system prompt injection
    # --------------------------------------------------------

    if system_prompt:
        payload["system"] = system_prompt

    # --------------------------------------------------------
    # Send request
    # --------------------------------------------------------

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_CONFIG.TIMEOUT
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise LLMError(f"Ollama request failed: {str(e)}")

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    try:
        data = response.json()

    except json.JSONDecodeError:
        raise LLMError("Invalid JSON returned from Ollama.")

    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if "response" not in data:
        raise LLMError(
            "Ollama response missing 'response' field."
        )

    return data["response"].strip()
