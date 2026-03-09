from typing import (
    ClassVar,
    Generic,
    TypeVar,
    Any,
    get_args,
    get_origin,
    Self,
)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from dataclasses import dataclass
from workflow.models.hook_input import (
    PreToolUseInput,
    PostToolUseInput,
    UserPromptSubmitInput,
    StopInput,
    ToolInputType,
)
from workflow.models.hook_output import (
    PreToolUseOutput,
    PreToolUseHSO,
    GeneralHSO,
    PostToolUseOutput,
    UserPromptSubmitOutput,
    StopOutput,
)


class Hook:

    @staticmethod
    def read_stdin() -> dict[str, Any]:
        try:
            raw = sys.stdin.read()
            if not raw.strip():
                print("Error: empty stdin", file=sys.stderr)
                sys.exit(1)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON on stdin: {e}", file=sys.stderr)
            sys.exit(1)

    @staticmethod
    def block(message: str) -> None:
        print(message, file=sys.stderr)
        sys.exit(2)

    @staticmethod
    def success_response(message: str) -> None:
        print(message)
        sys.exit(0)

    @staticmethod
    def debug(message: str) -> None:
        print(message)
        sys.exit(1)

    @staticmethod
    def advanced_output(output: dict[str, Any]) -> None:
        print(json.dumps(output))
        sys.exit(0)
