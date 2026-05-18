import requests


class LLM:

    def __init__(
        self,
        model="llama3.2:latest",
        base_url="http://localhost:11434",
        timeout=60,
        max_retries=1
    ):
        self.model = model
        self.url = f"{base_url}/v1/chat/completions"
        self.timeout = timeout
        self.max_retries = max_retries

    # ====================================================
    # MAIN GENERATION
    # ====================================================

    def generate(self, prompt, temperature=0.2):

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "stream": False
        }

        last_error = None

        for attempt in range(self.max_retries + 1):

            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout
                )

                response.raise_for_status()

                data = response.json()
                content = self._extract_content(data)

                if content is None or not isinstance(content, str):
                    raise ValueError("Empty or invalid LLM response")

                return content.strip()

            except requests.exceptions.Timeout as e:
                last_error = f"LLM timeout: {e}"

            except requests.exceptions.RequestException as e:
                last_error = f"LLM request error: {e}"

            except Exception as e:
                last_error = f"LLM processing error: {e}"

        # If all retries fail
        raise RuntimeError(last_error or "Unknown LLM failure")

    # ====================================================
    # RESPONSE EXTRACTION
    # ====================================================

    def _extract_content(self, data):

        try:
            return (
                data
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", None)
            )
        except Exception as e:
            raise RuntimeError(f"Malformed LLM response structure: {e}")
