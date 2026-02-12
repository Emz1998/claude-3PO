#!/usr/bin/env python3
"""Tests for normalize_skill_name utility function."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.unified_loader import normalize_skill_name  # type: ignore


class TestNormalizeSkillName:
    """Tests for normalize_skill_name function."""

    def test_strips_workflow_prefix(self):
        """Should strip 'workflow:' prefix from skill name."""
        assert normalize_skill_name("workflow:explore") == "explore"

    def test_strips_workflow_prefix_plan(self):
        """Should strip 'workflow:' prefix from plan skill."""
        assert normalize_skill_name("workflow:plan") == "plan"

    def test_strips_workflow_prefix_code(self):
        """Should strip 'workflow:' prefix from code skill."""
        assert normalize_skill_name("workflow:code") == "code"

    def test_leaves_unprefixed_name_unchanged(self):
        """Should leave skill names without prefix unchanged."""
        assert normalize_skill_name("explore") == "explore"

    def test_leaves_other_prefixes_unchanged(self):
        """Should not strip other prefixes like 'dry-run:'."""
        assert normalize_skill_name("dry-run:explore") == "dry-run:explore"

    def test_handles_empty_string(self):
        """Should handle empty string gracefully."""
        assert normalize_skill_name("") == ""

    def test_handles_workflow_only(self):
        """Should handle 'workflow:' with no phase name."""
        assert normalize_skill_name("workflow:") == ""

    def test_case_sensitive(self):
        """Should be case sensitive - only lowercase 'workflow:' is stripped."""
        assert normalize_skill_name("Workflow:explore") == "Workflow:explore"
        assert normalize_skill_name("WORKFLOW:explore") == "WORKFLOW:explore"

    def test_preserves_nested_colons(self):
        """Should only strip first 'workflow:' prefix."""
        assert normalize_skill_name("workflow:phase:subphase") == "phase:subphase"
