#!/usr/bin/env python3
"""Pytest tests for phase reminders with external file support."""

import sys
from pathlib import Path

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from context.phase_reminders import (  # type: ignore
    get_phase_reminder,
    get_all_phase_reminders,
    get_available_phases,
    clear_cache,
    REMINDERS_DIR,
    DEFAULT_REMINDERS,
)


@pytest.fixture(autouse=True)
def clear_reminder_cache():
    """Clear cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


class TestFileLoading:
    """Test loading reminders from external markdown files."""

    def test_load_from_file_returns_content(self):
        """get_phase_reminder loads content from markdown file."""
        reminder = get_phase_reminder("explore")
        assert reminder is not None
        assert len(reminder) > 0

    def test_loaded_content_is_markdown(self):
        """Loaded content starts with markdown header."""
        reminder = get_phase_reminder("explore")
        assert reminder.startswith("## Phase: EXPLORE")

    def test_all_standard_phases_load(self):
        """All 11 standard phases load successfully."""
        expected_phases = [
            "explore", "plan", "plan-consult", "finalize-plan",
            "write-test", "review-test", "write-code", "code-review",
            "refactor", "validate", "commit"
        ]
        for phase in expected_phases:
            reminder = get_phase_reminder(phase)
            assert reminder is not None, f"Phase {phase} failed to load"
            assert len(reminder) > 50, f"Phase {phase} content too short"

    def test_nonexistent_phase_returns_none(self):
        """Non-existent phase without default returns None."""
        reminder = get_phase_reminder("nonexistent-phase-xyz")
        assert reminder is None


class TestCaching:
    """Test caching behavior for performance."""

    def test_cache_returns_same_content(self):
        """Second call returns cached content."""
        reminder1 = get_phase_reminder("explore")
        reminder2 = get_phase_reminder("explore")
        assert reminder1 == reminder2

    def test_cache_bypass_still_returns_content(self):
        """use_cache=False still returns valid content."""
        reminder1 = get_phase_reminder("explore", use_cache=True)
        reminder2 = get_phase_reminder("explore", use_cache=False)
        assert reminder1 == reminder2

    def test_clear_cache_allows_reload(self):
        """clear_cache allows fresh file read."""
        reminder1 = get_phase_reminder("explore")
        clear_cache()
        reminder2 = get_phase_reminder("explore")
        assert reminder1 == reminder2


class TestFallback:
    """Test fallback to defaults when files missing."""

    def test_fallback_keys_match_standard_phases(self):
        """DEFAULT_REMINDERS contains all standard phases."""
        expected = {
            "explore", "plan", "plan-consult", "finalize-plan",
            "write-test", "review-test", "write-code", "code-review",
            "refactor", "validate", "commit"
        }
        assert set(DEFAULT_REMINDERS.keys()) == expected

    def test_fallback_content_not_empty(self):
        """Each fallback has non-empty content."""
        for phase, content in DEFAULT_REMINDERS.items():
            assert len(content) > 10, f"Fallback for {phase} too short"

    def test_fallback_used_when_file_missing(self):
        """Returns default when file doesn't exist."""
        test_file = REMINDERS_DIR / "explore.md"
        if not test_file.exists():
            pytest.skip("Test requires explore.md to exist first")

        # Temporarily rename file
        backup_file = REMINDERS_DIR / "explore.md.bak"
        test_file.rename(backup_file)
        try:
            clear_cache()
            reminder = get_phase_reminder("explore")
            assert reminder == DEFAULT_REMINDERS["explore"]
        finally:
            backup_file.rename(test_file)


class TestAvailablePhases:
    """Test phase discovery functionality."""

    def test_returns_sorted_list(self):
        """get_available_phases returns sorted list."""
        phases = get_available_phases()
        assert phases == sorted(phases)

    def test_contains_standard_phases(self):
        """Contains all 11 standard phases."""
        phases = get_available_phases()
        expected = {
            "explore", "plan", "plan-consult", "finalize-plan",
            "write-test", "review-test", "write-code", "code-review",
            "refactor", "validate", "commit"
        }
        assert expected.issubset(set(phases))

    def test_discovers_new_phase_files(self):
        """Discovers new .md files as phases."""
        custom_file = REMINDERS_DIR / "custom-test-phase.md"
        custom_file.write_text("## Phase: CUSTOM-TEST\nTest content.")
        try:
            clear_cache()
            phases = get_available_phases()
            assert "custom-test-phase" in phases
        finally:
            custom_file.unlink()


class TestGetAllReminders:
    """Test bulk reminder retrieval."""

    def test_returns_dict(self):
        """get_all_phase_reminders returns dictionary."""
        reminders = get_all_phase_reminders()
        assert isinstance(reminders, dict)

    def test_contains_all_phases(self):
        """Dictionary contains all available phases."""
        reminders = get_all_phase_reminders()
        phases = get_available_phases()
        assert set(reminders.keys()) == set(phases)

    def test_all_values_are_strings(self):
        """All reminder values are non-empty strings."""
        reminders = get_all_phase_reminders()
        for phase, content in reminders.items():
            assert isinstance(content, str), f"{phase} not a string"
            assert len(content) > 0, f"{phase} is empty"


class TestReminderContent:
    """Test reminder content structure and quality."""

    def test_explore_has_required_sections(self):
        """Explore reminder contains expected sections."""
        reminder = get_phase_reminder("explore")
        assert "Purpose:" in reminder
        assert "Deliverables:" in reminder
        assert "Next Phase:" in reminder

    def test_commit_indicates_workflow_complete(self):
        """Commit reminder indicates workflow completion."""
        reminder = get_phase_reminder("commit")
        assert "Workflow Complete" in reminder

    def test_write_test_mentions_tdd_red(self):
        """Write-test reminder mentions TDD Red phase."""
        reminder = get_phase_reminder("write-test")
        assert "TDD Red" in reminder or "Red" in reminder

    def test_write_code_mentions_tdd_green(self):
        """Write-code reminder mentions TDD Green phase."""
        reminder = get_phase_reminder("write-code")
        assert "TDD Green" in reminder or "Green" in reminder


class TestRemindersDirectory:
    """Test reminders directory configuration."""

    def test_reminders_dir_exists(self):
        """REMINDERS_DIR points to existing directory."""
        assert REMINDERS_DIR.exists()
        assert REMINDERS_DIR.is_dir()

    def test_reminders_dir_contains_md_files(self):
        """Directory contains markdown files."""
        md_files = list(REMINDERS_DIR.glob("*.md"))
        assert len(md_files) >= 11

    def test_reminders_dir_path_is_correct(self):
        """REMINDERS_DIR path is config/reminders."""
        assert REMINDERS_DIR.name == "reminders"
        assert REMINDERS_DIR.parent.name == "config"


class TestModuleImports:
    """Test module can be imported correctly."""

    def test_import_from_context_module(self):
        """Can import from context module."""
        from context import (  # type: ignore
            get_phase_reminder,
            get_all_phase_reminders,
            get_available_phases,
            clear_cache,
        )
        assert callable(get_phase_reminder)
        assert callable(get_all_phase_reminders)
        assert callable(get_available_phases)
        assert callable(clear_cache)

    def test_get_phase_reminder_signature(self):
        """get_phase_reminder accepts phase and use_cache params."""
        # Should not raise
        get_phase_reminder("explore", use_cache=True)
        get_phase_reminder("explore", use_cache=False)
