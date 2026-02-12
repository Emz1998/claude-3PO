#!/usr/bin/env python3
"""Pytest tests for the stop handler module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handlers.stop import main  # type: ignore


class TestStopHandler:
    """Tests for Stop handler."""

    def test_stop_deactivates_workflow_when_active(self):
        """Stop hook deactivates workflow when active."""
        with patch("handlers.stop.read_stdin_json") as mock_stdin, \
             patch("handlers.stop.get_manager") as mock_manager:
            mock_stdin.return_value = {"hook_event_name": "Stop", "stop_hook_active": False}
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_state.get_current_phase.return_value = "explore"
            mock_manager.return_value = mock_state

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_state.deactivate_workflow.assert_called_once()
            mock_state.set.assert_any_call("stopped_phase", "explore")

    def test_stop_does_nothing_when_workflow_inactive(self):
        """Stop hook does nothing when workflow is inactive."""
        with patch("handlers.stop.read_stdin_json") as mock_stdin, \
             patch("handlers.stop.get_manager") as mock_manager:
            mock_stdin.return_value = {"hook_event_name": "Stop", "stop_hook_active": False}
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = False
            mock_manager.return_value = mock_state

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_state.deactivate_workflow.assert_not_called()

    def test_stop_ignores_non_stop_events(self):
        """Stop handler ignores non-Stop events."""
        with patch("handlers.stop.read_stdin_json") as mock_stdin, \
             patch("handlers.stop.get_manager") as mock_manager:
            mock_stdin.return_value = {"hook_event_name": "SubagentStop"}
            mock_state = MagicMock()
            mock_manager.return_value = mock_state

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_state.deactivate_workflow.assert_not_called()

    def test_stop_stores_stop_info(self):
        """Stop handler stores stop metadata."""
        with patch("handlers.stop.read_stdin_json") as mock_stdin, \
             patch("handlers.stop.get_manager") as mock_manager:
            mock_stdin.return_value = {"hook_event_name": "Stop", "stop_hook_active": True}
            mock_state = MagicMock()
            mock_state.is_workflow_active.return_value = True
            mock_state.get_current_phase.return_value = "refactor"
            mock_manager.return_value = mock_state

            with pytest.raises(SystemExit):
                main()

            # Verify stop info stored
            calls = mock_state.set.call_args_list
            call_dict = {c[0][0]: c[0][1] for c in calls}
            assert call_dict["stopped_phase"] == "refactor"
            assert call_dict["stop_hook_active"] is True
            assert "stopped_at" in call_dict

    def test_stop_exits_early_on_empty_input(self):
        """Stop handler exits early on empty input."""
        with patch("handlers.stop.read_stdin_json") as mock_stdin, \
             patch("handlers.stop.get_manager") as mock_manager:
            mock_stdin.return_value = None
            mock_state = MagicMock()
            mock_manager.return_value = mock_state

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_state.deactivate_workflow.assert_not_called()


class TestImports:
    """Tests for module imports."""

    def test_main_import(self):
        """main function can be imported."""
        from handlers.stop import main
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
