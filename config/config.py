import os
from dataclasses import dataclass
from pathlib import Path


# ============================================================
# BASE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MEMORY_DIR = BASE_DIR / "memory"
LOG_DIR = BASE_DIR / "logs"

MEMORY_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

@dataclass
class OllamaConfig:
    """
    Configuration for local Ollama LLM runtime.
    """

    BASE_URL: str = "http://localhost:11434"
    GENERATE_ENDPOINT: str = "/api/generate"

    MODEL: str = "llama3.2"
    TEMPERATURE: float = 0.4

    STREAM: bool = False
    TIMEOUT: int = 120


# ============================================================
# AGENT LOOP CONFIGURATION
# ============================================================

@dataclass
class AgentConfig:
    """
    Controls orchestrator behavior and retry logic.
    """

    MAX_RETRIES_PER_STEP: int = 3
    MAX_REPLANS_PER_TASK: int = 5

    ENABLE_CRITIC: bool = True
    ENABLE_MEMORY: bool = True

    VERBOSE_LOGGING: bool = True


# ============================================================
# MEMORY CONFIGURATION
# ============================================================

@dataclass
class MemoryConfig:
    """
    Memory and persistence settings.
    """

    SQLITE_DB_PATH: str = str(MEMORY_DIR / "nextmind.db")

    MAX_SHORT_TERM_ITEMS: int = 25

    AUTO_SUMMARIZE: bool = False


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

@dataclass
class LoggingConfig:
    """
    Logging and debugging settings.
    """

    LOG_FILE: str = str(LOG_DIR / "nextmind.log")

    SAVE_AGENT_STEPS: bool = True
    SAVE_TOOL_CALLS: bool = True

    LOG_LEVEL: str = "INFO"


# ============================================================
# TOOL EXECUTION CONFIGURATION
# ============================================================

@dataclass
class ToolConfig:
    """
    Safety boundaries for tool execution.
    """

    ENABLE_FILE_WRITE: bool = True
    ENABLE_FILE_DELETE: bool = False

    ALLOWED_FILE_EXTENSIONS = [
        ".txt",
        ".md",
        ".py",
        ".json",
        ".html",
        ".css",
        ".js",
    ]

    MAX_FILE_WRITE_SIZE: int = 100_000  # bytes


# ============================================================
# GLOBAL CONFIG INSTANCE
# ============================================================

OLLAMA_CONFIG = OllamaConfig()
AGENT_CONFIG = AgentConfig()
MEMORY_CONFIG = MemoryConfig()
LOGGING_CONFIG = LoggingConfig()
TOOL_CONFIG = ToolConfig()
