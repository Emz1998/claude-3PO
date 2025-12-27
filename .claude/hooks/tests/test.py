import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import read_stdin_json, write_file, read_file  # type: ignore


def main() -> None:
    hook_input = read_stdin_json()
    current_content = read_file("pre_tool_test.log")
    write_file(
        "pre_tool_test.log", current_content + "\n" + json.dumps(hook_input, indent=4)
    )
    print("Successfully wrote to pre_tool_test.log")


if __name__ == "__main__":
    main()
