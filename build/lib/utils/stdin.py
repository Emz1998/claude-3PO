import sys
import json
from typing import Any


def read_stdin_json() -> dict[str, Any]:
    """Parse JSON from stdin. Returns empty dict on error."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}
