import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Set {name} in your environment or .env file before running.")
    return value


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    """Application configuration. The model never reads this object directly."""

    openai_api_key: str
    tavily_api_key: str
    openai_model: str
    max_output_tokens: int
    max_model_calls: int
    max_tool_calls: int
    tavily_max_results: int
    langsmith_tracing: bool
    langsmith_api_key: str | None
    langsmith_project: str

    @classmethod
    def from_env(cls, *, env_file: str | None = ".env") -> "Settings":
        load_dotenv(env_file)

        tracing_raw = os.getenv("LANGSMITH_TRACING", "false").strip().lower()
        langsmith_tracing = tracing_raw in {"1", "true", "yes", "on"}

        return cls(
            openai_api_key=_require("OPENAI_API_KEY"),
            tavily_api_key=_require("TAVILY_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            max_output_tokens=_optional_int("MAX_OUTPUT_TOKENS", 1200),
            max_model_calls=_optional_int("MAX_MODEL_CALLS", 4),
            max_tool_calls=_optional_int("MAX_TOOL_CALLS", 3),
            tavily_max_results=_optional_int("TAVILY_MAX_RESULTS", 5),
            langsmith_tracing=langsmith_tracing,
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "job-research-agent"),
        )

    def apply_langsmith_env(self) -> None:
        """LangChain reads these process env vars when tracing is enabled."""
        if not self.langsmith_tracing:
            return
        os.environ["LANGSMITH_TRACING"] = "true"
        if self.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
