"""Decision guard — blocks stop if /decision was not invoked.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads state.json and checks validation.decision_invoked == true.
"""

import sys
from pathlib import Path

from workflow.state_store import StateStore
from workflow.hook import Hook
from workflow.validation_log import log

STATE_PATH = Path(".claude/hooks/workflow/state.json")


def main() -> None:
    store = StateStore(STATE_PATH)
    state = store.load()
    validation = state.get("validation", {})
    decision_invoked = validation.get("decision_invoked", False)

    if not decision_invoked:
        msg = "You must invoke /decision <confidence_score> <quality_score> before stopping."
        log("decision_guard", "BLOCK", msg)
        Hook.block(msg)

    log("decision_guard", "ALLOW", "decision_invoked=true")
    sys.exit(0)


if __name__ == "__main__":
    main()
