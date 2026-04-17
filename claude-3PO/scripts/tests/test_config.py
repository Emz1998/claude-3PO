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


class TestSpecsSchemas:
    def test_architecture_schema_exists(self, config):
        schema = config.specs_schema("architecture")
        assert "Project Name" in schema["metadata_fields"]
        assert "Draft" in schema["valid_statuses"]

    def test_architecture_required_sections(self, config):
        sections = config.specs_required_sections("architecture")
        assert "1. Project Overview" in sections
        assert "13. Appendix" in sections

    def test_architecture_required_subsections(self, config):
        subs = config.specs_required_subsections("architecture")
        assert "1.1 Purpose & Business Context" in subs["1. Project Overview"]

    def test_architecture_valid_statuses(self, config):
        statuses = config.specs_valid_statuses("architecture")
        assert statuses == ["Draft", "In Review", "Approved"]

    def test_architecture_metadata_fields(self, config):
        assert config.specs_metadata_fields("architecture") == [
            "Project Name", "Version", "Date", "Author(s)", "Status"
        ]

    def test_architecture_allowed_extras(self, config):
        extras = config.specs_allowed_extra_sections("architecture")
        assert "Table of Contents" in extras

    def test_constitution_schema(self, config):
        schema = config.specs_schema("constitution")
        assert "Governing Principles" in schema["required_h1_sections"]

    def test_product_vision_required_tables(self, config):
        tables = config.specs_required_tables("product_vision")
        assert any(t["section"] == "Who Has This Problem?" for t in tables)

    def test_backlog_item_types(self, config):
        assert config.specs_valid_item_types("backlog") == ["US", "TS", "BG", "SK"]

    def test_backlog_priorities(self, config):
        assert config.specs_valid_priorities("backlog") == ["P0", "P1", "P2"]

    def test_backlog_story_type_names(self, config):
        names = config.specs_story_type_names("backlog")
        assert names["US"] == "User Story"
        assert names["BG"] == "Bug"

    def test_sprint_table_headers(self, config):
        headers = config.specs_schema("sprint")["overview_table_headers"]
        assert "ID" in headers and "Blocked By" in headers

    def test_unknown_doc_returns_empty_schema(self, config):
        assert config.specs_schema("does_not_exist") == {}

    def test_unknown_doc_returns_empty_lists(self, config):
        assert config.specs_required_sections("does_not_exist") == []
        assert config.specs_required_subsections("does_not_exist") == {}
        assert config.specs_required_tables("does_not_exist") == []
        assert config.specs_valid_priorities("does_not_exist") == []
