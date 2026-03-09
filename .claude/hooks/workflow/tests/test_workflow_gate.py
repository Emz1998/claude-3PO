"""Tests for workflow_gate — activation state management."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from workflow.workflow_gate import is_workflow_active


class TestIsWorkflowActive:
    def test_true(self):
        assert is_workflow_active({"workflow_active": True}) is True

    def test_false(self):
        assert is_workflow_active({"workflow_active": False}) is False

    def test_missing_key(self):
        assert is_workflow_active({}) is False


class TestActivateDeactivate:
    def test_activate_workflow(self, tmp_path):
        """activate_workflow() sets workflow_active=True in state."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        with patch("workflow.workflow_gate.state_store") as mock_store:
            from workflow.workflow_gate import activate_workflow
            activate_workflow()
            mock_store.set.assert_called_once_with("workflow_active", True)

    def test_deactivate_workflow(self, tmp_path):
        """deactivate_workflow() sets workflow_active=False in state."""
        with patch("workflow.workflow_gate.state_store") as mock_store:
            from workflow.workflow_gate import deactivate_workflow
            deactivate_workflow()
            mock_store.set.assert_called_once_with("workflow_active", False)


class TestCheckWorkflowGate:
    def test_active(self):
        """Returns True when state has workflow_active=True."""
        mock_store_instance = MagicMock()
        mock_store_instance.load.return_value = {"workflow_active": True}

        with patch("workflow.workflow_gate.StateStore", return_value=mock_store_instance):
            from workflow.workflow_gate import check_workflow_gate
            result = check_workflow_gate()
        assert result is True

    def test_inactive(self):
        """Returns False when state has workflow_active=False."""
        mock_store_instance = MagicMock()
        mock_store_instance.load.return_value = {"workflow_active": False}

        with patch("workflow.workflow_gate.StateStore", return_value=mock_store_instance):
            from workflow.workflow_gate import check_workflow_gate
            result = check_workflow_gate()
        assert result is False

    def test_no_state(self):
        """Returns False when state is None."""
        mock_store_instance = MagicMock()
        mock_store_instance.load.return_value = None

        with patch("workflow.workflow_gate.StateStore", return_value=mock_store_instance):
            from workflow.workflow_gate import check_workflow_gate
            result = check_workflow_gate()
        assert result is False
