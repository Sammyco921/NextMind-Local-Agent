import requests


class LLM:

    def __init__(
        self,
        model="llama3.2:latest",
        base_url="http://localhost:11434",
        timeout=60
    ):
        self.model = model
        self.url = f"{base_url}/v1/chat/completions"
        self.timeout = timeout

    # ====================================================
    # CORE GENERATION
    # ====================================================

    def generate(self, prompt, temperature=0.2):

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

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

            return self._extract_content(data)

        except requests.exceptions.Timeout:
            raise RuntimeError("LLM timeout: model took too long to respond")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM request failed: {e}")

        except Exception as e:
            raise RuntimeError(f"LLM parsing failed: {e}")

    # ====================================================
    # SAFE RESPONSE EXTRACTION
    # ====================================================

    def _extract_content(self, data):

        try:
            return (
                data
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
        except Exception:
            raise RuntimeError(f"Malformed LLM response: {data}")
