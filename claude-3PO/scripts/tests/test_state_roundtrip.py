"""Schema roundtrip tests for models.state.State.

Loads every fixture under tests/fixtures/state_snapshots/ and asserts
that every JSON line round-trips through ``State.model_validate(d).model_dump()``
without dropping or mutating user-visible fields.

If you add a fixture, this test ensures the model can ingest it. If the live
state.jsonl shape evolves, copy a fresh snapshot into fixtures/ and re-run.
"""

import json
from pathlib import Path

import pytest

from models.state import State


FIXTURES = Path(__file__).parent / "fixtures" / "state_snapshots"


def _load_snapshot_lines() -> list[dict]:
    snapshots = []
    for fp in sorted(FIXTURES.glob("*.jsonl")):
        for line in fp.read_text().splitlines():
            line = line.strip()
            if line:
                snapshots.append(json.loads(line))
    return snapshots


@pytest.mark.parametrize("snapshot", _load_snapshot_lines())
def test_snapshot_validates_under_state_model(snapshot):
    State.model_validate(snapshot)


@pytest.mark.parametrize("snapshot", _load_snapshot_lines())
def test_snapshot_roundtrip_preserves_all_keys(snapshot):
    """Dumped form must contain every original top-level key."""
    model = State.model_validate(snapshot)
    dumped = model.model_dump(exclude_unset=False)
    for key in snapshot:
        assert key in dumped, f"Top-level key {key!r} dropped during roundtrip"


def test_default_state_validates():
    """The conftest DEFAULT_STATE shape (build/implement workflows) must validate too."""
    from conftest import DEFAULT_STATE

    State.model_validate(DEFAULT_STATE)
