"""Decision guard — blocks stop if /decision was not invoked.

Placement: Reviewer agent frontmatter as a Stop hook.
Reads session state and checks validation.decision_invoked == true.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.session_state import SessionState
from workflow.hook import Hook
from workflow.validation.validation_log import log
from workflow.workflow_gate import check_workflow_gate


def main() -> None:
    is_workflow_active = check_workflow_gate()
    if not is_workflow_active:
        return

    session = SessionState()
    story_id = session.story_id

    if story_id:
        session_data = session.get_session(story_id)
        if session_data:
            validation = session_data.get("validation", {})
            decision_invoked = validation.get("decision_invoked", False)
        else:
            decision_invoked = False
    else:
        # Fallback: read from flat state
        from workflow.state_store import StateStore
        from workflow.config import get as cfg
        store = StateStore(Path(cfg("paths.workflow_state")))
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
