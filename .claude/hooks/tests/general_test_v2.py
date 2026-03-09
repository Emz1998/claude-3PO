import sys
import json
from pathlib import Path


FILE_PATH = Path("general-test-v2.log")


def read_stdin_json() -> dict:
    return json.loads(sys.stdin.read())


def main() -> None:
    hook_input = read_stdin_json()
    if not FILE_PATH.parent.exists():
        FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not FILE_PATH.exists():
        FILE_PATH.touch()
    log_content = FILE_PATH.read_text()
    FILE_PATH.write_text(f"{log_content}\n{json.dumps(hook_input, indent=4)}")
    print(f"Successfully wrote to {FILE_PATH}")


if __name__ == "__main__":
    main()
