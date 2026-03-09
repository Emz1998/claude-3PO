"""Tests for validate_order() — phase/agent ordering validation."""

import pytest

from workflow.utils.order_validation import validate_order


ORDER = ["explore", "plan", "code", "validate", "push"]


class TestValidateOrder:
    def test_valid_first_step(self):
        """None -> first item is valid."""
        valid, msg = validate_order(None, "explore", ORDER)
        assert valid is True
        assert msg == ""

    def test_valid_sequential(self):
        """Sequential forward transition is valid."""
        valid, msg = validate_order("explore", "plan", ORDER)
        assert valid is True
        assert msg == ""

    def test_valid_repeat(self):
        """Same item repeated is valid (index diff == 0)."""
        valid, msg = validate_order("plan", "plan", ORDER)
        assert valid is True

    def test_invalid_backwards(self):
        """Backwards transition is invalid."""
        valid, msg = validate_order("code", "explore", ORDER)
        assert valid is False
        assert "backwards" in msg.lower()

    def test_invalid_skip(self):
        """Skipping a step is invalid."""
        valid, msg = validate_order("explore", "code", ORDER)
        assert valid is False
        assert "plan" in msg.lower()

    def test_invalid_next_item(self):
        """Unknown next_item is invalid."""
        valid, msg = validate_order("explore", "unknown", ORDER)
        assert valid is False
        assert "invalid next item" in msg.lower()

    def test_invalid_current_item(self):
        """Unknown current_item is invalid."""
        valid, msg = validate_order("unknown", "explore", ORDER)
        assert valid is False
        assert "invalid current item" in msg.lower()

    def test_none_current_valid_first(self):
        """None current with first item is valid."""
        valid, _ = validate_order(None, "explore", ORDER)
        assert valid is True

    def test_none_current_invalid_non_first(self):
        """None current with non-first item is invalid."""
        valid, msg = validate_order(None, "plan", ORDER)
        assert valid is False
        assert "must start with" in msg.lower()
