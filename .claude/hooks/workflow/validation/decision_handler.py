"""Decision handler — PreToolUse hook for Skill(decision).

Intercepts /decision <confidence_score> <quality_score> invocations,
validates args, and writes scores to state.json.
Blocks with self-correction message if args are invalid.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.state_store import StateStore
from workflow.hook import Hook
from workflow.validation.validation_log import log
from workflow.config import get as cfg

STATE_PATH = Path(cfg("paths.workflow_state"))


def main() -> None:
    hook_input = Hook.read_stdin()

    tool_name = hook_input.get("tool_name")
    tool_input = hook_input.get("tool_input", {})
    skill_name = tool_input.get("skill", "")

    if tool_name != "Skill" or skill_name != "decision":
        sys.exit(0)

    args_str = tool_input.get("args", "").strip()
    parts = args_str.split()

    if len(parts) != 2:
        msg = "Invalid /decision args. Expected exactly 2 arguments: /decision <confidence_score> <quality_score> (integers 1-100)."
        log("decision_handler", "BLOCK", f"args='{args_str}' — {msg}")
        Hook.block(msg)

    try:
        confidence_score = int(parts[0])
        quality_score = int(parts[1])
    except ValueError:
        msg = "Invalid /decision args. Both scores must be integers: /decision <confidence_score> <quality_score> (integers 1-100)."
        log("decision_handler", "BLOCK", f"args='{args_str}' — {msg}")
        Hook.block(msg)

    if not (1 <= confidence_score <= 100) or not (1 <= quality_score <= 100):
        msg = f"Scores out of range (confidence={confidence_score}, quality={quality_score}). Both must be integers between 1 and 100."
        log("decision_handler", "BLOCK", msg)
        Hook.block(msg)

    store = StateStore(STATE_PATH)
    state = store.load() or {}
    existing = state.get("validation") or {}
    state["validation"] = {
        "decision_invoked": True,
        "confidence_score": confidence_score,
        "quality_score": quality_score,
        "iteration_count": existing.get("iteration_count", 0),
    }
    store.save(state)
    log("decision_handler", "ALLOW", f"confidence={confidence_score}, quality={quality_score}")


if __name__ == "__main__":
    main()
