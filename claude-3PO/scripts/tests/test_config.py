"""Tests for config.py — dual workflow phases and get_phases()."""

import pytest
from config import Config


class TestGetPhases:
    def test_build_phases(self, config):
        phases = config.get_phases("build")
        assert "explore" in phases
        assert "create-tasks" in phases
        assert "install-deps" in phases
        assert "define-contracts" in phases
        assert "write-report" in phases

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


class TestAgentMaxCount:
    """get_agent_max_count reads agent_count from phase entries."""

    def test_explore_agent_count(self, config):
        assert config.get_agent_max_count("Explore") == 3

    def test_research_agent_count(self, config):
        assert config.get_agent_max_count("Research") == 3

    def test_plan_agent_count(self, config):
        assert config.get_agent_max_count("Plan") == 1

    def test_plan_review_agent_count(self, config):
        assert config.get_agent_max_count("PlanReview") == 3

    def test_architect_agent_count(self, config):
        assert config.get_agent_max_count("Architect") == 1

    def test_product_owner_agent_count(self, config):
        assert config.get_agent_max_count("ProductOwner") == 1

    def test_unknown_agent_defaults_to_1(self, config):
        assert config.get_agent_max_count("UnknownAgent") == 1


class TestSpecsPhases:
    """Specs workflow should have its own phase set."""

    def test_specs_phases(self, config):
        phases = config.get_phases("specs")
        assert phases == ["vision", "strategy", "decision", "architect", "backlog"]

    def test_specs_phases_order(self, config):
        phases = config.get_phases("specs")
        assert phases.index("vision") < phases.index("strategy")
        assert phases.index("strategy") < phases.index("decision")
        assert phases.index("decision") < phases.index("architect")
        assert phases.index("architect") < phases.index("backlog")


class TestSpecsPaths:
    """Config should expose specs doc paths."""

    def test_product_vision_path(self, config):
        assert config.product_vision_file_path == "projects/docs/product-vision.md"

    def test_decisions_path(self, config):
        assert config.decisions_file_path == "projects/docs/decisions.md"

    def test_architecture_path(self, config):
        assert config.architecture_file_path == "projects/docs/architecture.md"

    def test_backlog_md_path(self, config):
        assert config.backlog_md_file_path == "projects/docs/backlog.md"

    def test_backlog_json_path(self, config):
        assert config.backlog_json_file_path == "projects/docs/backlog.json"
