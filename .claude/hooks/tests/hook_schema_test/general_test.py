import sys
import argparse
import json
from pathlib import Path


DEFAULT_FILE_PATH = Path("general-test.log")


def read_stdin_json() -> dict:
    return json.loads(sys.stdin.read())


def test_log(content: str, file_path: Path = DEFAULT_FILE_PATH) -> None:
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        file_path.touch()
    log_content = file_path.read_text()
    file_path.write_text(f"{log_content}\n{content}")


def main() -> None:
    hook_input = read_stdin_json()
    test_log(json.dumps(hook_input, indent=4))


if __name__ == "__main__":
    main()
