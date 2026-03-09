"""Decision guard — blocks stop if /decision was not invoked.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads state.json and checks validation.decision_invoked == true.
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
    store = StateStore(STATE_PATH)
    state = store.load()
    validation = state.get("validation", {})
    decision_invoked = validation.get("decision_invoked", False)

    if not decision_invoked:
        msg = "You must invoke /decision <confidence_score> <quality_score> before stopping."
        log("decision_guard", "BLOCK", msg)
        Hook.block(msg)

    # log("decision_guard", "ALLOW", "decision_invoked=true")
    sys.exit(0)


if __name__ == "__main__":
    main()
