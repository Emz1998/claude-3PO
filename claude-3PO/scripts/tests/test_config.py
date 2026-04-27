"""Tests for config.py — implement-only phases and get_phases()."""

import pytest
from config import Config


EXPECTED_IMPLEMENT_PHASES = [
    "explore",
    "research",
    "plan",
    "create-tasks",
    "write-tests",
    "write-code",
    "write-report",
]


class TestGetPhases:
    def test_implement_phases(self, config):
        phases = config.get_phases("implement")
        assert phases == EXPECTED_IMPLEMENT_PHASES

    def test_unknown_workflow_returns_empty(self, config):
        phases = config.get_phases("unknown")
        assert phases == []

    def test_implement_phases_order(self, config):
        phases = config.get_phases("implement")
        assert phases.index("explore") < phases.index("plan")
        assert phases.index("plan") < phases.index("create-tasks")
        assert phases.index("create-tasks") < phases.index("write-tests")
        assert phases.index("write-code") < phases.index("write-report")


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
    def test_create_tasks_no_agent(self, config):
        assert config.get_required_agent("create-tasks") == ""

    def test_plan_agent(self, config):
        assert config.get_required_agent("plan") == "Plan"


class TestAgentMaxCount:
    """get_agent_max_count reads agent_count from phase entries."""

    def test_explore_agent_count(self, config):
        assert config.get_agent_max_count("Explore") == 3

    def test_research_agent_count(self, config):
        assert config.get_agent_max_count("Research") == 2

    def test_plan_agent_count(self, config):
        assert config.get_agent_max_count("Plan") == 1

    def test_unknown_agent_defaults_to_1(self, config):
        assert config.get_agent_max_count("UnknownAgent") == 1


class TestCheckpointPhase:
    def test_plan_is_checkpoint(self, config):
        assert config.is_checkpoint_phase("plan")


class TestTemplatesDir:
    def test_templates_dir_resolves_to_plugin_templates(self, config):
        assert config.templates_dir.name == "templates"
        assert config.templates_dir.is_dir()
