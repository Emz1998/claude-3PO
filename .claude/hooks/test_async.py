import sys
from pathlib import Path
import json
import subprocess

sys.path.insert(0, str(Path(__file__).parent))
from utils.stdin import read_stdin_json


def run_reviewer() -> str:
    result = subprocess.run(
        [
            "claude",
            "hello claude! whats the date today?",
            "--tools",
            "Skill,Read,Grep,Glob",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout


def main() -> None:
    hook_input = read_stdin_json()
    # tool_name = hook_input.get("tool_name", "")
    # if tool_name != "Skill":
    #     sys.exit(0)

    # skill_name = hook_input.get("tool_input", {}).get("skill", "")
    # if skill_name != "test-1":
    #     print(f"Skill name is {skill_name}, expected test-1")
    #     sys.exit(2)

    # review_result = run_reviewer()

    sys.stdout.write("Hello, world!\n")


if __name__ == "__main__":
    main()
