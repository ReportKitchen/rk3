"""Loader for LLM prompts kept as editable files under the repo-root `prompts/`
directory (NOT in docs/ — these are load-bearing code assets that ship with the
engine). Every system prompt, rubric, and instruction the code sends to a model
lives there as a reviewable .md/.txt file so it can be read and edited without
tracing through Python.

Prompts are read FRESH on every call (no caching) so editing a prompt file takes
effect on the next model call without a process restart."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Return the text of prompts/<name>, stripped of a trailing newline. Raises
    FileNotFoundError if the prompt file is missing — a missing prompt is a bug,
    not a silent fallback."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").rstrip("\n")
