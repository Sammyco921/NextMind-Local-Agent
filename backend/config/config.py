import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class OllamaConfig:
    BASE_URL: str = "http://localhost:11434"
    GENERATE_ENDPOINT: str = "/api/generate"
    MODEL: str = "llama3.2"
    TEMPERATURE: float = 0.4
    STREAM: bool = False
    TIMEOUT: int = 120


@dataclass
class LoggingConfig:
    LOG_FILE: str = str(LOG_DIR / "nextmind.log")
    SAVE_TOOL_CALLS: bool = True
    LOG_LEVEL: str = "INFO"


@dataclass
class ToolConfig:
    ENABLE_FILE_WRITE: bool = True
    ALLOWED_FILE_EXTENSIONS = [".txt", ".md", ".py", ".json", ".html", ".css", ".js"]
    MAX_FILE_WRITE_SIZE: int = 100_000


OLLAMA_CONFIG = OllamaConfig()
LOGGING_CONFIG = LoggingConfig()
TOOL_CONFIG = ToolConfig()
