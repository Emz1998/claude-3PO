"""Tests for utils/template_schema.TemplateSchema.

Parses the real template markdown files under claude-3PO/templates/ and
asserts the parsed schema values match the structure those templates
encode — which is the same shape the old config.specs_schemas block
used to hold, just derived from the template instead of duplicated.
"""

from pathlib import Path

import pytest

from utils.template_schema import TemplateSchema

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


# ═══════════════════════════════════════════════════════════════════
# Architecture
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def architecture_schema() -> TemplateSchema:
    return TemplateSchema.from_file(_TEMPLATES_DIR / "architecture.md", "architecture")


class TestArchitectureSchema:
    def test_metadata_fields_from_bold_block(self, architecture_schema):
        fields = architecture_schema.metadata_fields
        for expected in ("Project Name", "Version", "Date", "Author(s)", "Status"):
            assert expected in fields

    def test_status_enum_parsed_from_inline_slashes(self, architecture_schema):
        assert architecture_schema.status_enums["Status"] == [
            "Draft", "In Review", "Approved"
        ]

    def test_required_sections_only_numbered_h2(self, architecture_schema):
        sections = architecture_schema.required_sections
        assert "1. Project Overview" in sections
        assert "13. Appendix" in sections
        assert "Table of Contents" not in sections

    def test_table_of_contents_is_allowed_extra(self, architecture_schema):
        assert "Table of Contents" in architecture_schema.allowed_extra_sections

    def test_numbered_h3_subsections_captured(self, architecture_schema):
        subs = architecture_schema.required_subsections
        assert "1.1 Purpose & Business Context" in subs["1. Project Overview"]
        assert "6.5 Data Lifecycle" in subs["6. Security Architecture"]
        assert "12.3 Risks" in subs["12. Risks, Assumptions & Constraints"]

    def test_unnumbered_h3s_excluded(self, architecture_schema):
        subs = architecture_schema.required_subsections
        assert "Failure Scenarios" not in subs.get(
            "10. Reliability & Disaster Recovery", []
        )
        assert "Revision History" not in subs.get("13. Appendix", [])


# ═══════════════════════════════════════════════════════════════════
# Constitution
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def constitution_schema() -> TemplateSchema:
    return TemplateSchema.from_file(_TEMPLATES_DIR / "constitution.md", "constitution")


class TestConstitutionSchema:
    def test_blockquote_metadata_parsed(self, constitution_schema):
        fields = constitution_schema.metadata_fields
        assert fields == ["Project", "Version", "Last Updated", "Maintained by"]

    def test_doc_title_captured(self, constitution_schema):
        assert constitution_schema.doc_title == "Project Constitution"

    def test_required_h1_sections(self, constitution_schema):
        sections = constitution_schema.required_sections
        for expected in (
            "Governing Principles",
            "Development Guidelines",
            "Coding Standards",
            "Testing Policy",
            "Definition of Done",
            "Tooling",
        ):
            assert expected in sections
        assert "Project Constitution" not in sections

    def test_h2_subsections_under_h1(self, constitution_schema):
        subs = constitution_schema.required_subsections
        assert "Workflow" in subs["Development Guidelines"]
        assert "Security" in subs["Development Guidelines"]
        assert "Language & Type Safety" in subs["Coding Standards"]
        assert "Required Tests" in subs["Testing Policy"]
        assert "Task Done" in subs["Definition of Done"]

    def test_h3_subsections_for_version_control(self, constitution_schema):
        h3 = constitution_schema.required_h3_subsections
        assert h3["Version Control"] == ["Branch Naming", "Commit Messages"]

    def test_h3_subsections_for_code_structure(self, constitution_schema):
        h3 = constitution_schema.required_h3_subsections
        assert "Directory Structure" in h3["Code Structure"]


# ═══════════════════════════════════════════════════════════════════
# Product Vision
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def product_vision_schema() -> TemplateSchema:
    return TemplateSchema.from_file(
        _TEMPLATES_DIR / "product-vision.md", "product_vision"
    )


class TestProductVisionSchema:
    def test_bold_metadata_fields(self, product_vision_schema):
        assert product_vision_schema.metadata_fields == [
            "Project", "Version", "Author", "Last Updated"
        ]

    def test_required_sections(self, product_vision_schema):
        sections = product_vision_schema.required_sections
        for expected in (
            "Vision Statement",
            "The Problem",
            "The Solution",
            "Market Landscape",
            "Strategy",
            "Business Model",
            "Risks & Mitigations",
            "Team & Resources",
            "Success Criteria",
            "Appendix",
            "Document History",
        ):
            assert expected in sections

    def test_required_subsections(self, product_vision_schema):
        subs = product_vision_schema.required_subsections
        assert "Who Has This Problem?" in subs["The Problem"]
        assert "Core Value Propositions" in subs["The Solution"]
        assert "MVP Scope" in subs["Strategy"]
        assert "Glossary" in subs["Appendix"]

    def test_required_tables_include_segment(self, product_vision_schema):
        tables = product_vision_schema.required_tables
        segment = next((t for t in tables if t["section"] == "Who Has This Problem?"), None)
        assert segment is not None
        assert segment["required_header"] == "Segment"

    def test_required_tables_include_value_proposition(self, product_vision_schema):
        tables = product_vision_schema.required_tables
        vp = next((t for t in tables if t["section"] == "Core Value Propositions"), None)
        assert vp is not None
        assert vp["required_header"] in ("#", "Value Proposition")

    def test_required_tables_include_document_history(self, product_vision_schema):
        tables = product_vision_schema.required_tables
        dh = next((t for t in tables if t["section"] == "Document History"), None)
        assert dh is not None
        assert dh["required_header"] == "Version"


# ═══════════════════════════════════════════════════════════════════
# Backlog
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def backlog_schema() -> TemplateSchema:
    return TemplateSchema.from_file(_TEMPLATES_DIR / "backlog.md", "backlog")


class TestBacklogSchema:
    def test_bold_metadata_fields(self, backlog_schema):
        assert backlog_schema.metadata_fields == ["Project", "Last Updated"]

    def test_required_sections(self, backlog_schema):
        sections = backlog_schema.required_sections
        assert sections == ["Priority Legend", "ID Conventions", "Stories"]

    def test_priority_legend_parsed(self, backlog_schema):
        assert backlog_schema.valid_priorities == ["P0", "P1", "P2"]

    def test_item_types_parsed_from_id_conventions(self, backlog_schema):
        assert set(backlog_schema.valid_item_types) == {"US", "TS", "SK", "BG"}

    def test_story_type_names_parsed(self, backlog_schema):
        names = backlog_schema.story_type_names
        assert names["US"] == "User Story"
        assert names["TS"] == "Technical Story"
        assert names["SK"] == "Spike"
        assert names["BG"] == "Bug"

    def test_json_item_statuses_from_sample(self, backlog_schema):
        statuses = set(backlog_schema.json_item_statuses)
        assert {"Backlog", "In Progress", "Done", "Blocked"}.issubset(statuses)
