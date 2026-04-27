"""Tests for utils/extractors.py — plan section and contract name extraction."""

import pytest

try:
    from lib.extractors import (
        extract_plan_dependencies,
        extract_plan_tasks,
        extract_bold_metadata,
    )
except ImportError:
    extract_plan_dependencies = None
    extract_plan_tasks = None
    extract_bold_metadata = None

_not_implemented = pytest.mark.skipif(
    extract_plan_dependencies is None,
    reason="Not yet implemented",
)


# ═══════════════════════════════════════════════════════════════════
# extract_plan_dependencies
# ═══════════════════════════════════════════════════════════════════


@_not_implemented
class TestExtractPlanDependencies:
    def test_extracts_bullet_items(self):
        content = (
            "# Plan\n\n"
            "## Dependencies\n"
            "- flask\n"
            "- sqlalchemy\n"
            "- pytest\n\n"
            "## Tasks\n"
            "- Build login\n"
        )
        deps = extract_plan_dependencies(content)
        assert deps == ["flask", "sqlalchemy", "pytest"]

    def test_empty_section(self):
        content = "# Plan\n\n## Dependencies\n\n## Tasks\n- something\n"
        deps = extract_plan_dependencies(content)
        assert deps == []

    def test_no_dependencies_section(self):
        content = "# Plan\n\n## Tasks\n- Build login\n"
        deps = extract_plan_dependencies(content)
        assert deps == []

    def test_strips_whitespace(self):
        content = "## Dependencies\n-   flask   \n-  pytest  \n"
        deps = extract_plan_dependencies(content)
        assert deps == ["flask", "pytest"]

    def test_ignores_non_bullet_content(self):
        content = (
            "## Dependencies\n"
            "Some description text.\n"
            "- flask\n"
            "Another paragraph.\n"
            "- pytest\n"
        )
        deps = extract_plan_dependencies(content)
        assert deps == ["flask", "pytest"]


# ═══════════════════════════════════════════════════════════════════
# extract_plan_tasks
# ═══════════════════════════════════════════════════════════════════


@_not_implemented
class TestExtractPlanTasks:
    def test_extracts_bullet_items(self):
        content = (
            "# Plan\n\n"
            "## Tasks\n"
            "- Build authentication module\n"
            "- Create user database schema\n"
            "- Write API endpoints\n"
        )
        tasks = extract_plan_tasks(content)
        assert tasks == [
            "Build authentication module",
            "Create user database schema",
            "Write API endpoints",
        ]

    def test_empty_section(self):
        content = "# Plan\n\n## Tasks\n\n## Other\n"
        tasks = extract_plan_tasks(content)
        assert tasks == []

    def test_no_tasks_section(self):
        content = "# Plan\n\n## Dependencies\n- flask\n"
        tasks = extract_plan_tasks(content)
        assert tasks == []

    def test_strips_whitespace(self):
        content = "## Tasks\n-   Build login   \n-  Create schema  \n"
        tasks = extract_plan_tasks(content)
        assert tasks == ["Build login", "Create schema"]

    def test_tasks_after_other_sections(self):
        content = (
            "## Goals\n- ship\n\n"
            "## Tasks\n"
            "- Implement auth\n"
            "- Write tests\n"
        )
        tasks = extract_plan_tasks(content)
        assert tasks == ["Implement auth", "Write tests"]


# ═══════════════════════════════════════════════════════════════════
# extract_bold_metadata
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(extract_bold_metadata is None, reason="Not yet implemented")
class TestExtractBoldMetadata:
    def test_extracts_simple_pairs(self):
        content = (
            "# Doc\n\n"
            "**Project:** Acme\n"
            "**Version:** 1.0\n"
            "**Author:** Dev Team\n\n"
            "## Section\n"
        )
        meta = extract_bold_metadata(content)
        assert meta["Project"] == "Acme"
        assert meta["Version"] == "1.0"
        assert meta["Author"] == "Dev Team"

    def test_strips_backticks_around_value(self):
        content = "**Version:** `1.2.3`\n"
        assert extract_bold_metadata(content)["Version"] == "1.2.3"

    def test_ignores_placeholder_values(self):
        content = (
            "**Project:** [your project]\n"
            "**Version:** <TBD>\n"
            "**Status:** Draft\n"
        )
        meta = extract_bold_metadata(content)
        # Placeholders are returned as-is — caller decides how to flag them.
        assert meta["Project"].startswith("[")
        assert meta["Version"].startswith("<")
        assert meta["Status"] == "Draft"

    def test_empty_when_no_metadata(self):
        assert extract_bold_metadata("# Doc\n\nNo metadata here.\n") == {}

    def test_multiple_colons_kept_in_value(self):
        content = "**URL:** https://example.com:8080/path\n"
        assert extract_bold_metadata(content)["URL"] == "https://example.com:8080/path"

    def test_handles_composite_field_names(self):
        content = (
            "**Last Updated:** 2026-04-16\n"
            "**Author(s):** Alice, Bob\n"
            "**Maintained by:** Platform Team\n"
        )
        meta = extract_bold_metadata(content)
        assert meta["Last Updated"] == "2026-04-16"
        assert meta["Author(s)"] == "Alice, Bob"
        assert meta["Maintained by"] == "Platform Team"
