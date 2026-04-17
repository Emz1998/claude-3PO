"""Tests for Recorder.TOOL_RECORDERS dispatch map."""

import pytest

from utils.recorder import Recorder


def test_tool_recorders_map_keys():
    assert set(Recorder.TOOL_RECORDERS.keys()) == {"Skill", "Write", "Edit", "Bash"}


def test_tool_recorders_map_values_are_callable():
    for fn in Recorder.TOOL_RECORDERS.values():
        assert callable(fn)


def test_unknown_tool_is_a_noop(state, config):
    rec = Recorder(state)
    # No exception, no state mutation:
    rec.record({"tool_name": "Mystery", "tool_input": {}}, config)


def test_record_dispatches_to_skill_handler(state, config, monkeypatch):
    rec = Recorder(state)
    called = {}

    def fake_skill(self, tool_input, phase):
        called["skill"] = (tool_input, phase)

    monkeypatch.setattr(Recorder, "_record_skill", fake_skill)
    rec.record({"tool_name": "Skill", "tool_input": {"k": "v"}}, config)
    assert called["skill"] == ({"k": "v"}, state.current_phase)
