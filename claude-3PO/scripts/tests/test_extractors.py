"""Tests for utils/extractors.py — plan section and contract name extraction."""

import pytest

try:
    from lib.extractors import (
        extract_plan_dependencies,
        extract_plan_tasks,
        extract_contract_names,
    )
except ImportError:
    extract_plan_dependencies = None
    extract_plan_tasks = None
    extract_contract_names = None

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
            "## Dependencies\n- flask\n\n"
            "## Contracts\n- UserService\n\n"
            "## Tasks\n"
            "- Implement auth\n"
            "- Write tests\n"
        )
        tasks = extract_plan_tasks(content)
        assert tasks == ["Implement auth", "Write tests"]


# ═══════════════════════════════════════════════════════════════════
# extract_contract_names
# ═══════════════════════════════════════════════════════════════════


@_not_implemented
class TestExtractContractNames:
    def test_extracts_bullet_items(self):
        content = (
            "# Contracts\n\n"
            "- UserService\n"
            "- AuthProvider\n"
            "- DatabaseClient\n"
        )
        names = extract_contract_names(content)
        assert names == ["UserService", "AuthProvider", "DatabaseClient"]

    def test_empty_content(self):
        names = extract_contract_names("")
        assert names == []

    def test_no_bullet_items(self):
        content = "# Contracts\n\nSome text with no bullets.\n"
        names = extract_contract_names(content)
        assert names == []

    def test_strips_whitespace(self):
        content = "-   UserService   \n-  AuthProvider  \n"
        names = extract_contract_names(content)
        assert names == ["UserService", "AuthProvider"]

    def test_extracts_from_headings(self):
        content = (
            "## UserService\n"
            "Description of UserService.\n\n"
            "## AuthProvider\n"
            "Description of AuthProvider.\n"
        )
        names = extract_contract_names(content)
        assert "UserService" in names
        assert "AuthProvider" in names
