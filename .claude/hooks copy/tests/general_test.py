import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, write_file, read_file  # type: ignore

FILE_PATH = Path("general-test.log")


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
