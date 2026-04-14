"""Temporary test helper to populate code_files_to_write and complete write-code phase."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/emhar/avaris-ai/claudeguard/scripts")))

from utils.state_store import StateStore
from utils.resolvers import resolve_write_code
from config import Config

STATE_PATH = Path("/home/emhar/avaris-ai/claudeguard/scripts/state.jsonl")
state = StateStore(STATE_PATH, session_id="83b11a30-a014-4fb7-8707-ca08395fc3a5")
state.add_code_file_to_write("/home/emhar/avaris-ai/src/hello.py")
resolve_write_code(state)


def test_write_code_completed():
    assert state.is_phase_completed("write-code"), "write-code should be completed"
