import sys
import argparse
import json
from pathlib import Path


DEFAULT_FILE_PATH = Path("general-test.log")


def read_stdin_json() -> dict:
    return json.loads(sys.stdin.read())


def test_log(file_path: Path = DEFAULT_FILE_PATH) -> None:
    hook_input = read_stdin_json()
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        file_path.touch()
    log_content = file_path.read_text()
    file_path.write_text(f"{log_content}\n{json.dumps(hook_input, indent=4)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-path", type=Path, default=DEFAULT_FILE_PATH)
    args = parser.parse_args()
    test_log(args.file_path)


if __name__ == "__main__":
    main()
