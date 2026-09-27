from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"


def load_system_prompt() -> str:
    if not _PROMPT_PATH.is_file():
        raise FileNotFoundError(f"Missing system prompt file: {_PROMPT_PATH}")
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()
