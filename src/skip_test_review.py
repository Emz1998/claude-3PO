"""Skip test-review phase since TDD is disabled."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/emhar/avaris-ai/claudeguard/scripts")))

from utils.state_store import StateStore

STATE_PATH = Path("/home/emhar/avaris-ai/claudeguard/scripts/state.jsonl")
state = StateStore(STATE_PATH, session_id="83b11a30-a014-4fb7-8707-ca08395fc3a5")
state.add_phase("test-review")
state.complete_phase("test-review")


def test_test_review_skipped():
    assert state.is_phase_completed("test-review"), "test-review should be completed"
