import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import read_stdin_json, get_cache, set_cache  # type: ignore
from validate_invocations import track_subagents  # type: ignore


MAIN_PHASES_ORDER = ["explore", "plan", "code"]
CODE_PHASES_ORDER = ["test", "commit", "implement", "code-review", "commit"]
current_main_phase = "explore"


def block_phase_advancement(next_phase: str, phases_order: list[str]) -> bool:
    next_phase_index = phases_order.index(next_phase)
    current_phase_index = phases_order.index(current_main_phase)
    if next_phase_index == current_phase_index:
        print(f"You are already in the {next_phase} phase")
        return True
    elif next_phase_index < current_phase_index:
        print(f"You cannot advance the phase from {current_main_phase} to {next_phase}")
        return True
    else:
        print(f"You can advance the phase from {current_main_phase} to {next_phase}")
        return False


def main() -> None:
    hook_input = read_stdin_json()

    skill = hook_input.get("tool_input", {}).get("skill", "")
    tdd = skill.get("args", "")
    if block_phase_advancement(next_phase, MAIN_PHASES_ORDER):
        return
    if not code_phase_guard(tdd, next_phase, CODE_PHASES_ORDER):
        sys.exit(2)
    set_cache("workflow_state", current_main_phase)
    sys.exit(0)


if __name__ == "__main__":
    main()
