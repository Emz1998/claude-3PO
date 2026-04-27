import json
from pathlib import Path
from typing_extensions import Literal


DEFAULT_PROMPT_DIR = Path(__file__).parent.parent.parent / "prompts"


def build_prompt_path(prompt_name: Literal["research", "explore"]) -> Path:
    return DEFAULT_PROMPT_DIR / f"{prompt_name}.md"


def retrieve_prompt(prompt_name: Literal["research", "explore"]) -> str:
    with open(build_prompt_path(prompt_name), "r") as file:
        return file.read()
