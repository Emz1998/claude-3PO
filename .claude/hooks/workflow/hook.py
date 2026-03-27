from typing import (
    Any,
)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json


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
    def advanced_output(output: dict[str, Any]) -> None:
        print(json.dumps(output))
        sys.exit(0)

    @staticmethod
    def block(message: str) -> None:
        print(message, file=sys.stderr)
        sys.exit(2)

    @staticmethod
    def advanced_block(hook_event_name: str, message: str) -> None:
        output = {
            "hookSpecificOutput": {
                "hookEventName": hook_event_name,
                "permissionDecision": "deny",
                "permissionDecisionReason": message,
            },
        }
        Hook.advanced_output(output)

    @staticmethod
    def success_response(message: str) -> None:
        print(message)
        sys.exit(0)

    @staticmethod
    def debug(message: str) -> None:
        print(message, file=sys.stderr)
        sys.exit(1)

    @staticmethod
    def system_message(message: str) -> None:
        print(json.dumps({"systemMessage": message}))
        sys.exit(0)
