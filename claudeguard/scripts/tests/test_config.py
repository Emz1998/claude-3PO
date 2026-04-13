"""Tests for config.py — dual workflow phases and get_phases()."""

import pytest
from config import Config


class TestGetPhases:
    def test_build_phases(self, config):
        phases = config.get_phases("build")
        assert "explore" in phases
        assert "install-deps" in phases
        assert "define-contracts" in phases
        assert "write-report" in phases
        # Build has install-deps and define-contracts
        assert "create-tasks" not in phases

    def test_implement_phases(self, config):
        phases = config.get_phases("implement")
        assert "explore" in phases
        assert "create-tasks" in phases
        assert "validate" in phases
        # Implement has NO install-deps or define-contracts
        assert "install-deps" not in phases
        assert "define-contracts" not in phases
        # Implement has validate instead of quality-check
        assert "quality-check" not in phases

    def test_unknown_workflow_returns_empty(self, config):
        phases = config.get_phases("unknown")
        assert phases == []

    def test_build_phases_order(self, config):
        phases = config.get_phases("build")
        # Verify ordering of key phases
        assert phases.index("explore") < phases.index("plan")
        assert phases.index("plan") < phases.index("plan-review")
        assert phases.index("write-code") < phases.index("code-review")
        assert phases.index("code-review") < phases.index("pr-create")

    def test_implement_phases_order(self, config):
        phases = config.get_phases("implement")
        assert phases.index("explore") < phases.index("plan")
        assert phases.index("plan-review") < phases.index("create-tasks")
        assert phases.index("create-tasks") < phases.index("write-tests")
        assert phases.index("write-code") < phases.index("validate")
        assert phases.index("validate") < phases.index("code-review")


class TestAutoPhases:
    def test_auto_phases_defined(self, config):
        auto = config.auto_phases
        assert "create-tasks" in auto
        assert "write-tests" in auto
        assert "write-code" in auto

    def test_is_auto_phase(self, config):
        assert config.is_auto_phase("create-tasks")
        assert config.is_auto_phase("write-tests")
        assert config.is_auto_phase("write-code")
        assert not config.is_auto_phase("plan")
        assert not config.is_auto_phase("explore")


class TestRequiredAgents:
    def test_validate_agent(self, config):
        assert config.get_required_agent("validate") == "QASpecialist"

    def test_create_tasks_no_agent(self, config):
        assert config.get_required_agent("create-tasks") == ""

    def test_tests_review_agent(self, config):
        assert config.get_required_agent("tests-review") == "TestReviewer"


class TestMainPhasesBackcompat:
    """MAIN_PHASES should still return the build phases for backward compat."""

    def test_main_phases_is_build(self, config):
        assert config.main_phases == config.get_phases("build")
