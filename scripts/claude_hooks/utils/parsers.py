import sys
import json
from pathlib import Path


PATH = Path.cwd() / "input-schemas"


def extract_slash_command_name(raw_command: str = "") -> str:
    """Extract command name from a slash-prefixed prompt."""
    if not raw_command or not raw_command.startswith("/"):
        return ""
    return raw_command[1:].split(" ")[0]


def main() -> None:
    """Main function."""
    for file in PATH.glob("*.log"):
        file.rename(file.with_suffix(".json"))


if __name__ == "__main__":
    main()
