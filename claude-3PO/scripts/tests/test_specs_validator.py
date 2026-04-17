"""Tests for utils/validator.py — SpecsValidator (all doc types)."""

from pathlib import Path

import pytest

from utils.validator import SpecsValidator

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXTURE_DIR = _PLUGIN_ROOT / "templates" / "test"


@pytest.fixture
def validator(config) -> SpecsValidator:
    return SpecsValidator(config)


# ═══════════════════════════════════════════════════════════════════
# Architecture
# ═══════════════════════════════════════════════════════════════════


_ARCH_METADATA = (
    "# Architecture\n\n"
    "**Project Name:** TestProj\n"
    "**Version:** 1.0\n"
    "**Date:** 2026-04-16\n"
    "**Author(s):** Alice\n"
    "**Status:** Draft\n"
    "**Last Reviewed:** 2026-04-16\n"
    "**Approved By:** Alice\n\n"
)

_ARCH_STRUCTURE_SECTIONS = [
    ("## 1. Project Overview", [
        "### 1.1 Purpose & Business Context",
        "### 1.2 Scope",
        "### 1.3 Definitions & Acronyms",
    ]),
    ("## 2. Architectural Decisions", [
        "### 2.1 Architecture Style",
        "### 2.2 Key Architecture Decision Records (ADRs)",
    ]),
    ("## 3. System Context & High-Level Architecture", [
        "### 3.1 System Context",
        "### 3.2 Architecture Diagram",
    ]),
    ("## 4. System Components", [
        "### 4.1 Project Structure Contract",
        "### 4.2 Frontend Layer",
        "### 4.3 API Layer",
        "### 4.4 Database Layer",
        "### 4.5 Database Client Pattern",
        "### 4.6 Migration Strategy",
        "### 4.7 Caching Strategy",
        "### 4.8 Service Communication",
    ]),
    ("## 5. Data Flow & Integration Patterns", [
        "### 5.1 Primary Request Flow",
        "### 5.2 Asynchronous Flows",
        "### 5.3 Third-Party Integrations",
        "### 5.4 Webhook Strategy",
    ]),
    ("## 6. Security Architecture", [
        "### 6.1 Authorization Model",
        "### 6.2 Authentication & Session Handling",
        "### 6.3 API & Network Protection",
        "### 6.4 Data Protection & Secrets",
        "### 6.5 Data Lifecycle",
    ]),
    ("## 7. Testing Strategy", []),
    ("## 8. Observability", [
        "### 8.1 Error Tracking",
        "### 8.2 Logging",
        "### 8.3 Request Correlation",
        "### 8.4 Uptime & Alerting",
    ]),
    ("## 9. DevOps & Deployment", [
        "### 9.1 Source Control & Branching",
        "### 9.2 Deployment",
        "### 9.3 Environments",
    ]),
    ("## 10. Reliability & Disaster Recovery", []),
    ("## 11. Cost & Operational Considerations", [
        "### 11.1 Monthly Cost Estimate",
        "### 11.2 Scaling Cost Triggers",
        "### 11.3 Vendor Lock-in Assessment",
    ]),
    ("## 12. Risks, Assumptions & Constraints", [
        "### 12.1 Assumptions",
        "### 12.2 Constraints",
        "### 12.3 Risks",
    ]),
    ("## 13. Appendix", []),
]


def _valid_architecture() -> str:
    body = []
    for section, subs in _ARCH_STRUCTURE_SECTIONS:
        body.append(section)
        body.append("Content.")
        for sub in subs:
            body.append(sub)
            body.append("Content.")
    return _ARCH_METADATA + "\n".join(body) + "\n"


class TestValidateArchitecture:
    def test_valid_doc_has_no_errors(self, validator):
        assert validator.validate_architecture(_valid_architecture()) == []

    def test_missing_metadata_flagged(self, validator):
        content = _valid_architecture().replace("**Version:** 1.0\n", "")
        errors = validator.validate_architecture(content)
        assert any("Version" in e for e in errors)

    def test_placeholder_metadata_flagged(self, validator):
        content = _valid_architecture().replace("**Project Name:** TestProj\n", "**Project Name:** [fill me]\n")
        errors = validator.validate_architecture(content)
        assert any("Project Name" in e and "placeholder" in e for e in errors)

    def test_invalid_status_flagged(self, validator):
        content = _valid_architecture().replace("**Status:** Draft\n", "**Status:** Shipped\n")
        errors = validator.validate_architecture(content)
        assert any("Status" in e and "Shipped" in e for e in errors)

    def test_missing_section_flagged(self, validator):
        content = _valid_architecture().replace("## 13. Appendix", "## Whatever Else")
        errors = validator.validate_architecture(content)
        assert any("13. Appendix" in e for e in errors)

    def test_missing_subsection_flagged(self, validator):
        content = _valid_architecture().replace("### 1.1 Purpose & Business Context\nContent.\n", "")
        errors = validator.validate_architecture(content)
        assert any("1.1 Purpose & Business Context" in e for e in errors)

    def test_table_of_contents_allowed_extra(self, validator):
        content = _valid_architecture().replace(
            "## 1. Project Overview",
            "## Table of Contents\n- links\n\n## 1. Project Overview",
        )
        errors = validator.validate_architecture(content)
        assert not any("Table of Contents" in e for e in errors)

    def test_unknown_section_flagged(self, validator):
        content = _valid_architecture() + "\n## Unknown Section\nContent.\n"
        errors = validator.validate_architecture(content)
        assert any("Unknown Section" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════
# Constitution
# ═══════════════════════════════════════════════════════════════════


_CONST_METADATA = (
    "# Project Constitution\n\n"
    "**Project:** Acme\n"
    "**Version:** 1.0\n"
    "**Last Updated:** 2026-04-16\n"
    "**Maintained by:** Platform Team\n\n"
)

_CONST_PRINCIPLES = (
    "# Governing Principles\n\n"
    "1. **Simplicity first:** keep it lean\n"
    "2. **Test-first:** TDD\n"
    "3. **Own it:** no finger-pointing\n"
    "4. **Readable code:** clarity over cleverness\n\n"
)

_CONST_DEV_GUIDELINES = (
    "# Development Guidelines\n\n"
    "## Workflow\ncontent\n\n"
    "## Decision-Making\ncontent\n\n"
    "## Dependencies\ncontent\n\n"
    "## Version Control\n"
    "### Branch Naming\ncontent\n"
    "### Commit Messages\ncontent\n\n"
    "## Security\ncontent\n\n"
)

_CONST_CODING_STANDARDS = (
    "# Coding Standards\n\n"
    "## Language & Type Safety\ncontent\n\n"
    "## Naming Conventions\ncontent\n\n"
    "## Formatting\ncontent\n\n"
    "## Code Structure\n"
    "### Directory Structure\ncontent\n\n"
    "## Comments & Documentation\ncontent\n\n"
    "## Error Handling\ncontent\n\n"
    "## AI-Specific Standards\n"
    "### Prompt Management\ncontent\n\n"
    "### Response Handling\ncontent\n\n"
    "### Performance & Cost\ncontent\n\n"
)

_CONST_TESTING = (
    "# Testing Policy\n\n"
    "## Required Tests\ncontent\n\n"
    "## Exempt from Tests\ncontent\n\n"
    "## Test Standards\ncontent\n\n"
)

_CONST_DOD = (
    "# Definition of Done\n\n"
    "## Task Done\n- [ ] code merged\n- [ ] tests pass\n\n"
    "## Story Done\n- [ ] all tasks done\n- [ ] reviewed\n\n"
    "## Sprint Done\n- [ ] demo\n- [ ] retro\n\n"
    "## Out of Scope\ncontent\n\n"
)

_CONST_TOOLING = (
    "# Tooling\n\n"
    "| Tool | Purpose |\n|------|---------|\n| pytest | testing |\n\n"
)

_CONST_APPENDIX = "# Appendix — Agent Reference\n\ncontent\n"


def _valid_constitution() -> str:
    return (
        _CONST_METADATA
        + _CONST_PRINCIPLES
        + _CONST_DEV_GUIDELINES
        + _CONST_CODING_STANDARDS
        + _CONST_TESTING
        + _CONST_DOD
        + _CONST_TOOLING
        + _CONST_APPENDIX
    )


class TestValidateConstitution:
    def test_valid_doc_has_no_errors(self, validator):
        assert validator.validate_constitution(_valid_constitution()) == []

    def test_missing_metadata_flagged(self, validator):
        content = _valid_constitution().replace("**Project:** Acme\n", "")
        errors = validator.validate_constitution(content)
        assert any("Project" in e for e in errors)

    def test_missing_h1_section_flagged(self, validator):
        content = _valid_constitution().replace("# Tooling", "# SomethingElse")
        errors = validator.validate_constitution(content)
        assert any("Tooling" in e for e in errors)

    def test_doc_title_not_flagged_as_unknown(self, validator):
        errors = validator.validate_constitution(_valid_constitution())
        assert not any("Project Constitution" in e and "unknown" in e for e in errors)

    def test_too_few_governing_principles_flagged(self, validator):
        content = _valid_constitution().replace(
            _CONST_PRINCIPLES,
            "# Governing Principles\n\n1. **Only one:** not enough\n\n",
        )
        errors = validator.validate_constitution(content)
        assert any("governing_principles" in e for e in errors)

    def test_missing_dod_checklist_flagged(self, validator):
        content = _valid_constitution().replace(
            "## Task Done\n- [ ] code merged\n- [ ] tests pass\n\n",
            "## Task Done\n\n",
        )
        errors = validator.validate_constitution(content)
        assert any("Task Done" in e for e in errors)

    def test_missing_tooling_table_flagged(self, validator):
        content = _valid_constitution().replace(
            "| Tool | Purpose |\n|------|---------|\n| pytest | testing |\n",
            "No table here.\n",
        )
        errors = validator.validate_constitution(content)
        assert any("tooling" in e.lower() for e in errors)

    def test_missing_h3_subsection_flagged(self, validator):
        content = _valid_constitution().replace(
            "### Branch Naming\ncontent\n", ""
        )
        errors = validator.validate_constitution(content)
        assert any("Branch Naming" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════
# Product Vision
# ═══════════════════════════════════════════════════════════════════


_PV_METADATA = (
    "# Product Vision\n\n"
    "**Project:** Acme\n"
    "**Version:** 1.0\n"
    "**Author:** Alice\n"
    "**Last Updated:** 2026-04-16\n\n"
)

_PV_SECTIONS = (
    "## Vision Statement\ncontent\n\n"
    "## The Problem\n"
    "### Who Has This Problem?\n"
    "| Segment | Description | Size |\n|---------|-------------|------|\n| SMB | small biz | 10k |\n\n"
    "### What's Broken Today?\ncontent\n\n"
    "### Why Now?\ncontent\n\n"
    "## The Solution\n"
    "### Product in One Paragraph\ncontent\n\n"
    "### Core Value Propositions\n"
    "| # | Value Proposition | User Benefit |\n|---|-------------------|-------------|\n| 1 | fast | saves time |\n\n"
    "### How It Works (High Level)\ncontent\n\n"
    "## Market Landscape\n"
    "### Competitive Positioning\n"
    "| Competitor / Alternative | Strength | Weakness |\n|----|----|----|\n| A | x | y |\n\n"
    "### Defensibility\ncontent\n\n"
    "## Strategy\n"
    "### MVP Scope\n"
    "| Feature | Priority |\n|---|---|\n| Auth | P0 |\n\n"
    "### What's Explicitly NOT in MVP\n"
    "| Excluded Feature | Why Not Yet |\n|---|---|\n| Widget | Later |\n\n"
    "### Product Roadmap (High Level)\n"
    "| Phase | Timeframe |\n|---|---|\n| MVP | Q1 |\n\n"
    "## Business Model\n"
    "### Revenue Model\n"
    "| Model | Description |\n|---|---|\n| SaaS | monthly |\n\n"
    "### Key Metrics\n"
    "| Metric | Definition | MVP Target |\n|---|---|---|\n| MAU | users | 1k |\n\n"
    "### Unit Economics (If Known)\n"
    "| Metric | Value |\n|---|---|\n| CAC | $10 |\n\n"
    "## Risks & Mitigations\n"
    "| Risk | Impact | Likelihood | Mitigation |\n|---|---|---|---|\n| Churn | High | Med | Focus on CX |\n\n"
    "## Team & Resources\n"
    "### Current Runway / Budget\ncontent\n\n"
    "| Role | Who | Status |\n|---|---|---|\n| Eng | Alice | Hired |\n\n"
    "## Success Criteria\n"
    "### MVP Launch (Go / No-Go)\ncontent\n\n"
    "### 6-Month Vision\ncontent\n\n"
    "### 12-Month Vision\ncontent\n\n"
    "## Appendix\n"
    "### Glossary\n"
    "| Term | Definition |\n|---|---|\n| API | Interface |\n\n"
    "### References\ncontent\n\n"
    "## Document History\n"
    "| Version | Date | Author | Changes |\n|---|---|---|---|\n| 1.0 | 2026-04-16 | Alice | initial |\n"
)


def _valid_product_vision() -> str:
    return _PV_METADATA + _PV_SECTIONS


class TestValidateProductVision:
    def test_valid_doc_has_no_errors(self, validator):
        assert validator.validate_product_vision(_valid_product_vision()) == []

    def test_missing_metadata_flagged(self, validator):
        content = _valid_product_vision().replace("**Author:** Alice\n", "")
        errors = validator.validate_product_vision(content)
        assert any("Author" in e for e in errors)

    def test_missing_section_flagged(self, validator):
        content = _valid_product_vision().replace("## Appendix\n", "## Something\n")
        errors = validator.validate_product_vision(content)
        assert any("Appendix" in e for e in errors)

    def test_missing_subsection_flagged(self, validator):
        content = _valid_product_vision().replace("### Why Now?\ncontent\n\n", "")
        errors = validator.validate_product_vision(content)
        assert any("Why Now?" in e for e in errors)

    def test_missing_required_table_flagged(self, validator):
        # Drop the "| Segment |" header only
        content = _valid_product_vision().replace(
            "| Segment | Description | Size |", "| X | Description | Size |"
        )
        errors = validator.validate_product_vision(content)
        assert any("Who Has This Problem?" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════
# Backlog MD + converter
# ═══════════════════════════════════════════════════════════════════


def _valid_backlog() -> str:
    return (
        "# Backlog\n\n"
        "**Project:** Acme\n"
        "**Last Updated:** 2026-04-16\n"
        "**Goal:** Ship MVP\n\n"
        "## Priority Legend\ncontent\n\n"
        "## ID Conventions\ncontent\n\n"
        "## Stories\n\n"
        "### US-001: Login\n\n"
        "> **As a** user, **I want** to log in **so that** I can use the app\n\n"
        "**Description:** Enable users to authenticate\n"
        "**Priority:** P0\n"
        "**Milestone:** MVP\n"
        "**Is Blocking:** None\n"
        "**Blocked By:** None\n\n"
        "- [ ] User can sign up\n"
        "- [ ] User can log in\n\n"
        "### BG-001: Fix crash\n\n"
        "> **What's broken:** Crash on logout\n"
        "> **Expected:** Clean logout\n"
        "> **Actual:** Crashes\n\n"
        "**Description:** Logout crash\n"
        "**Priority:** P1\n"
        "**Milestone:** Patch\n"
        "**Is Blocking:** None\n"
        "**Blocked By:** US-001\n\n"
        "- [ ] No crash on logout\n"
    )


class TestValidateBacklogMd:
    def test_valid_doc_has_no_errors(self, validator):
        assert validator.validate_backlog_md(_valid_backlog()) == []

    def test_missing_metadata_flagged(self, validator):
        content = _valid_backlog().replace("**Project:** Acme\n", "")
        assert any("Project" in e for e in validator.validate_backlog_md(content))

    def test_missing_stories_section_flagged(self, validator):
        content = _valid_backlog().replace("## Stories\n\n", "")
        errors = validator.validate_backlog_md(content)
        assert any("stories" in e.lower() or "Stories" in e for e in errors)

    def test_invalid_priority_flagged(self, validator):
        content = _valid_backlog().replace("**Priority:** P0\n", "**Priority:** P99\n")
        errors = validator.validate_backlog_md(content)
        assert any("P99" in e for e in errors)

    def test_unknown_item_type_flagged(self, validator):
        content = _valid_backlog().replace("### US-001:", "### XX-001:")
        errors = validator.validate_backlog_md(content)
        assert any("XX" in e for e in errors)

    def test_missing_us_blockquote_format_flagged(self, validator):
        content = _valid_backlog().replace(
            "> **As a** user, **I want** to log in **so that** I can use the app",
            "> No format here",
        )
        errors = validator.validate_backlog_md(content)
        assert any("US-001" in e for e in errors)

    def test_missing_bg_blockquote_format_flagged(self, validator):
        content = _valid_backlog().replace(
            "> **What's broken:** Crash on logout", "> Nothing"
        )
        errors = validator.validate_backlog_md(content)
        assert any("BG-001" in e for e in errors)

    def test_missing_acceptance_criteria_flagged(self, validator):
        content = _valid_backlog().replace(
            "- [ ] User can sign up\n- [ ] User can log in\n\n",
            "\n",
        )
        errors = validator.validate_backlog_md(content)
        assert any("US-001" in e and "acceptance_criteria" in e for e in errors)


class TestConvertBacklogMdToJson:
    def test_extracts_project_and_goal(self, validator):
        data = validator.convert_backlog_md_to_json(_valid_backlog())
        assert data["project"] == "Acme"
        assert data["goal"] == "Ship MVP"

    def test_extracts_stories(self, validator):
        data = validator.convert_backlog_md_to_json(_valid_backlog())
        ids = [s["id"] for s in data["stories"]]
        assert "US-001" in ids
        assert "BG-001" in ids

    def test_maps_story_type_from_prefix(self, validator):
        data = validator.convert_backlog_md_to_json(_valid_backlog())
        us = next(s for s in data["stories"] if s["id"] == "US-001")
        bg = next(s for s in data["stories"] if s["id"] == "BG-001")
        assert us["type"] == "User Story"
        assert bg["type"] == "Bug"

    def test_parses_acceptance_criteria(self, validator):
        data = validator.convert_backlog_md_to_json(_valid_backlog())
        us = next(s for s in data["stories"] if s["id"] == "US-001")
        assert us["acceptance_criteria"] == ["User can sign up", "User can log in"]

    def test_parses_blocked_by_list(self, validator):
        data = validator.convert_backlog_md_to_json(_valid_backlog())
        bg = next(s for s in data["stories"] if s["id"] == "BG-001")
        assert bg["blocked_by"] == ["US-001"]


# ═══════════════════════════════════════════════════════════════════
# Backlog JSON
# ═══════════════════════════════════════════════════════════════════


def _valid_story_json(story_id: str = "US-001", story_type: str = "User Story") -> dict:
    return {
        "id": story_id,
        "type": story_type,
        "title": "Login",
        "description": "Auth",
        "status": "Backlog",
        "priority": "P0",
        "milestone": "MVP",
        "is_blocking": [],
        "blocked_by": [],
        "acceptance_criteria": ["User can log in"],
        "item_type": "story",
        "start_date": "",
        "target_date": "",
    }


def _valid_backlog_json() -> dict:
    return {
        "project": "Acme",
        "goal": "Ship MVP",
        "dates": {"start": "2026-04-01", "end": "2026-04-30"},
        "totalPoints": 0,
        "stories": [_valid_story_json()],
    }


class TestValidateBacklogJson:
    def test_valid_data_has_no_errors(self, validator):
        assert validator.validate_backlog_json(_valid_backlog_json()) == []

    def test_missing_root_field_flagged(self, validator):
        data = _valid_backlog_json()
        del data["totalPoints"]
        errors = validator.validate_backlog_json(data)
        assert any("totalPoints" in e for e in errors)

    def test_invalid_status_flagged(self, validator):
        data = _valid_backlog_json()
        data["stories"][0]["status"] = "Shipped"
        errors = validator.validate_backlog_json(data)
        assert any("Shipped" in e for e in errors)

    def test_invalid_priority_flagged(self, validator):
        data = _valid_backlog_json()
        data["stories"][0]["priority"] = "P5"
        errors = validator.validate_backlog_json(data)
        assert any("P5" in e for e in errors)

    def test_unknown_type_flagged(self, validator):
        data = _valid_backlog_json()
        data["stories"][0]["type"] = "Saga"
        errors = validator.validate_backlog_json(data)
        assert any("Saga" in e for e in errors)

    def test_id_mismatch_flagged(self, validator):
        data = _valid_backlog_json()
        data["stories"][0]["id"] = "BG-001"  # Bug prefix, but type = User Story
        errors = validator.validate_backlog_json(data)
        assert any("does not match pattern" in e for e in errors)

    def test_bad_date_flagged(self, validator):
        data = _valid_backlog_json()
        data["dates"]["start"] = "04-01-2026"
        errors = validator.validate_backlog_json(data)
        assert any("YYYY-MM-DD" in e for e in errors)

    def test_item_type_must_be_story(self, validator):
        data = _valid_backlog_json()
        data["stories"][0]["item_type"] = "task"
        errors = validator.validate_backlog_json(data)
        assert any("item_type" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════
# E2E test fixtures (used by commands/test-specs.md)
# ═══════════════════════════════════════════════════════════════════


class TestE2EFixtures:
    """Fixtures under templates/test/ must validate clean so the live test runner
    has a known-good payload to feed to Architect / ProductOwner agents."""

    def test_minimal_architecture_fixture_is_valid(self, validator):
        path = _FIXTURE_DIR / "minimal-architecture.md"
        assert path.exists(), f"missing fixture: {path}"
        errors = validator.validate_architecture(path.read_text())
        assert errors == [], f"fixture not clean: {errors}"

    def test_minimal_backlog_fixture_is_valid(self, validator):
        path = _FIXTURE_DIR / "minimal-backlog.md"
        assert path.exists(), f"missing fixture: {path}"
        errors = validator.validate_backlog_md(path.read_text())
        assert errors == [], f"fixture not clean: {errors}"
