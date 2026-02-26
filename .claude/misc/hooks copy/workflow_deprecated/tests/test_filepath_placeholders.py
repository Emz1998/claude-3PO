#!/usr/bin/env python3
"""Tests for filepath placeholder resolution in deliverables.

Tests cover:
- Placeholder resolution ({project}, {session})
- Regex conversion from resolved paths
- Pattern matching behavior
- Backward compatibility with old folder/pattern/file syntax
- End-to-end integration
"""

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.unified_loader import (  # type: ignore
    FileDeliverable,
    parse_deliverable,
    resolve_filepath_placeholders,
    wildcard_to_regex,
)


def mock_project_module(return_path: Path | None = None, raise_error: bool = False):
    """Create a mock release_plan.project module."""
    mock_module = ModuleType("release_plan.project")
    if raise_error:
        mock_module.get_feature_path = MagicMock(side_effect=ImportError("No module"))
    else:
        mock_module.get_feature_path = MagicMock(
            return_value=return_path or Path("project/v0.1.0/EPIC-001/FEAT-001")
        )
    return mock_module


def mock_cache_module(session_id: str | None = "abc123", raise_error: bool = False):
    """Create a mock utils.cache module."""
    mock_module = ModuleType("utils.cache")
    if raise_error:
        mock_module.get_session_id = MagicMock(side_effect=ImportError("No module"))
    else:
        mock_module.get_session_id = MagicMock(return_value=session_id)
    return mock_module


class TestPlaceholderResolution:
    """Tests for resolve_filepath_placeholders function."""

    def test_project_placeholder_resolved(self):
        """Test {project} placeholder is resolved to feature path."""
        mock_proj = mock_project_module(Path("project/v0.1.0/EPIC-001/FEAT-001"))
        with patch.dict("sys.modules", {"release_plan.project": mock_proj}):
            result = resolve_filepath_placeholders("{project}/plans/foo.md")
            assert result == "project/v0.1.0/EPIC-001/FEAT-001/plans/foo.md"

    def test_session_placeholder_resolved(self):
        """Test {session} placeholder is resolved to session ID."""
        mock_cache = mock_cache_module("1ab7b734")
        with patch.dict("sys.modules", {"utils.cache": mock_cache}):
            result = resolve_filepath_placeholders("plans/foo_{session}.md")
            assert result == "plans/foo_1ab7b734.md"

    def test_both_placeholders_resolved(self):
        """Test both {project} and {session} are resolved together."""
        mock_proj = mock_project_module(Path("project/v0.1.0/EPIC-001/FEAT-001"))
        mock_cache = mock_cache_module("1ab7b734")
        with patch.dict(
            "sys.modules",
            {"release_plan.project": mock_proj, "utils.cache": mock_cache},
        ):
            result = resolve_filepath_placeholders("{project}/plans/foo_{session}.md")
            assert result == "project/v0.1.0/EPIC-001/FEAT-001/plans/foo_1ab7b734.md"

    def test_no_placeholders_unchanged(self):
        """Test paths without placeholders are returned unchanged."""
        result = resolve_filepath_placeholders("src/**/*.ts")
        assert result == "src/**/*.ts"

    def test_empty_string_unchanged(self):
        """Test empty string is returned unchanged."""
        result = resolve_filepath_placeholders("")
        assert result == ""

    def test_project_fallback_on_import_error(self):
        """Test {project}/ is removed when import fails."""
        mock_proj = mock_project_module(raise_error=True)
        with patch.dict("sys.modules", {"release_plan.project": mock_proj}):
            result = resolve_filepath_placeholders("{project}/plans/foo.md")
            assert result == "plans/foo.md"

    def test_project_fallback_on_empty_path(self):
        """Test {project}/ is removed when path is just 'project' (missing version/epic/feature)."""
        # Mock returns a path that when stringified contains "//" (indicates missing components)
        mock_module = ModuleType("release_plan.project")
        # Return a string directly that has "//" to trigger fallback
        mock_module.get_feature_path = MagicMock(return_value="project//")
        with patch.dict("sys.modules", {"release_plan.project": mock_module}):
            result = resolve_filepath_placeholders("{project}/plans/foo.md")
            assert result == "plans/foo.md"

    def test_session_fallback_to_wildcard(self):
        """Test {session} becomes * when session ID is not available."""
        mock_cache = mock_cache_module(None)
        with patch.dict("sys.modules", {"utils.cache": mock_cache}):
            result = resolve_filepath_placeholders("plans/foo_{session}.md")
            assert result == "plans/foo_*.md"

    def test_session_fallback_on_import_error(self):
        """Test {session} becomes * when import fails."""
        mock_cache = mock_cache_module(raise_error=True)
        with patch.dict("sys.modules", {"utils.cache": mock_cache}):
            result = resolve_filepath_placeholders("plans/foo_{session}.md")
            assert result == "plans/foo_*.md"


class TestRegexConversion:
    """Tests for wildcard to regex conversion with resolved paths."""

    def test_resolved_path_to_regex(self):
        """Test resolved filepath becomes valid regex."""
        resolved = "project/v0.1.0/EPIC-001/FEAT-001/plans/foo_1ab7b734.md"
        regex = wildcard_to_regex(f"**/{resolved}")
        assert re.match(regex, f"prefix/{resolved}")

    def test_wildcards_still_work_star(self):
        """Test * wildcard converted correctly after placeholder resolution."""
        resolved = "project/v0.1.0/EPIC-001/FEAT-001/plans/foo_*.md"
        regex = wildcard_to_regex(f"**/{resolved}")
        # Should match with any session ID
        assert re.match(regex, "project/v0.1.0/EPIC-001/FEAT-001/plans/foo_abc123.md")
        assert re.match(
            regex, "prefix/project/v0.1.0/EPIC-001/FEAT-001/plans/foo_xyz.md"
        )

    def test_wildcards_still_work_doublestar(self):
        """Test ** wildcard converted correctly."""
        regex = wildcard_to_regex("**/src/**/*.ts")
        assert re.match(regex, "src/components/Button.ts")
        assert re.match(regex, "prefix/src/deep/nested/file.ts")

    def test_question_mark_wildcard(self):
        """Test ? wildcard matches single character."""
        regex = wildcard_to_regex("**/foo?.md")
        assert re.match(regex, "foo1.md")
        assert re.match(regex, "prefix/fooA.md")
        assert not re.match(regex, "foo12.md")


class TestPatternMatching:
    """Tests for pattern matching with resolved paths."""

    def test_matches_correct_path(self):
        """Test regex matches exact resolved path."""
        resolved = "project/v0.1.0/EPIC-001/FEAT-001/plans/final-plan_abc123.md"
        regex = wildcard_to_regex(f"**/{resolved}")
        assert re.match(regex, resolved)
        assert re.match(regex, f"/home/user/repo/{resolved}")

    def test_rejects_wrong_feature(self):
        """Test regex rejects file from different feature."""
        resolved = "project/v0.1.0/EPIC-001/FEAT-001/plans/final-plan_abc123.md"
        regex = wildcard_to_regex(f"**/{resolved}")
        wrong_feature = "project/v0.1.0/EPIC-001/FEAT-002/plans/final-plan_abc123.md"
        assert not re.match(regex, wrong_feature)

    def test_rejects_wrong_session(self):
        """Test regex rejects file from different session."""
        resolved = "project/v0.1.0/EPIC-001/FEAT-001/plans/final-plan_abc123.md"
        regex = wildcard_to_regex(f"**/{resolved}")
        wrong_session = "project/v0.1.0/EPIC-001/FEAT-001/plans/final-plan_xyz789.md"
        assert not re.match(regex, wrong_session)

    def test_generic_matches_any(self):
        """Test non-placeholder path matches anywhere."""
        regex = wildcard_to_regex("**/src/**/*.ts")
        assert re.match(regex, "src/components/Button.ts")
        assert re.match(regex, "other/project/src/utils/helper.ts")


class TestExactMatch:
    """Tests for exact match using ./ prefix."""

    def test_exact_match_at_root(self):
        """Test ./ prefix creates exact match from repo root."""
        item = {"filepath": "./prompt.md"}
        deliverable = parse_deliverable(item, "read")
        regex = deliverable.regex_pattern
        # Should match at root
        assert re.match(regex, "prompt.md")
        # Should NOT match nested paths
        assert not re.match(regex, "nested/prompt.md")
        assert not re.match(regex, "/home/user/repo/prompt.md")

    def test_exact_match_with_subdirectory(self):
        """Test exact match with subdirectory path."""
        item = {"filepath": "./src/index.ts"}
        deliverable = parse_deliverable(item, "read")
        regex = deliverable.regex_pattern
        # Should match exact path
        assert re.match(regex, "src/index.ts")
        # Should NOT match with prefix
        assert not re.match(regex, "other/src/index.ts")

    def test_exact_match_with_wildcard(self):
        """Test exact match combined with wildcard."""
        item = {"filepath": "./src/*.ts"}
        deliverable = parse_deliverable(item, "read")
        regex = deliverable.regex_pattern
        # Should match files in src/ at root
        assert re.match(regex, "src/index.ts")
        assert re.match(regex, "src/utils.ts")
        # Should NOT match nested src/
        assert not re.match(regex, "nested/src/index.ts")

    def test_exact_match_preserves_filepath(self):
        """Test ./ is preserved in filepath field for display."""
        item = {"filepath": "./prompt.md"}
        deliverable = parse_deliverable(item, "read")
        assert deliverable.filepath == "./prompt.md"

    def test_non_exact_matches_anywhere(self):
        """Test without ./ prefix matches anywhere."""
        item = {"filepath": "prompt.md"}
        deliverable = parse_deliverable(item, "read")
        regex = deliverable.regex_pattern
        # Should match anywhere
        assert re.match(regex, "prompt.md")
        assert re.match(regex, "nested/prompt.md")
        assert re.match(regex, "/home/user/repo/prompt.md")


class TestBackwardCompatibility:
    """Tests for backward compatibility with old folder/pattern/file syntax."""

    def test_folder_pattern_still_works(self):
        """Test old folder/pattern syntax is converted to filepath."""
        item = {
            "folder": "plans",
            "pattern": "initial-plan_*.md",
            "description": "Initial plan",
        }
        deliverable = parse_deliverable(item, "read")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.filepath == "plans/initial-plan_*.md"
        assert deliverable.regex_pattern != ""

    def test_file_field_still_works(self):
        """Test old file field is converted to filepath."""
        item = {"file": "prompt.md", "description": "User prompt"}
        deliverable = parse_deliverable(item, "read")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.filepath == "prompt.md"
        assert deliverable.regex_pattern != ""

    def test_pattern_only_still_works(self):
        """Test pattern without folder is converted to filepath."""
        item = {"pattern": "*.md", "description": "Markdown files"}
        deliverable = parse_deliverable(item, "read")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.filepath == "*.md"

    def test_new_filepath_takes_precedence(self):
        """Test filepath field takes precedence over old fields."""
        item = {
            "filepath": "{project}/plans/new.md",
            "folder": "old",
            "pattern": "old.md",
        }
        deliverable = parse_deliverable(item, "read")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.filepath == "{project}/plans/new.md"


class TestParseDeliverable:
    """Tests for parse_deliverable function with new filepath field."""

    def test_filepath_with_project_placeholder(self):
        """Test parsing deliverable with {project} placeholder."""
        mock_proj = mock_project_module(Path("project/v0.1.0/EPIC-001/FEAT-001"))
        mock_cache = mock_cache_module("abc123")
        with patch.dict(
            "sys.modules",
            {"release_plan.project": mock_proj, "utils.cache": mock_cache},
        ):
            item = {
                "filepath": "{project}/plans/final-plan_{session}.md",
                "description": "Final plan",
                "strict_order": 1,
            }
            deliverable = parse_deliverable(item, "read")

            assert isinstance(deliverable, FileDeliverable)
            assert deliverable.filepath == "{project}/plans/final-plan_{session}.md"
            assert "FEAT-001" in deliverable.regex_pattern
            assert "abc123" in deliverable.regex_pattern

    def test_filepath_without_placeholders(self):
        """Test parsing deliverable without placeholders."""
        item = {
            "filepath": "src/**/*.ts",
            "description": "TypeScript files",
            "match": "source-files",
        }
        deliverable = parse_deliverable(item, "edit")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.filepath == "src/**/*.ts"
        assert deliverable.match == "source-files"

    def test_preserves_strict_order(self):
        """Test strict_order is preserved in parsed deliverable."""
        item = {
            "filepath": "{project}/plans/plan.md",
            "strict_order": 2,
        }
        deliverable = parse_deliverable(item, "read")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.strict_order == 2

    def test_preserves_match_group(self):
        """Test match group is preserved in parsed deliverable."""
        item = {
            "filepath": "src/**/*.test.ts",
            "match": "test-files",
        }
        deliverable = parse_deliverable(item, "write")
        assert isinstance(deliverable, FileDeliverable)
        assert deliverable.match == "test-files"


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_scoped_pattern_rejects_other_features(self):
        """Test scoped pattern only matches current feature's files."""
        mock_proj = mock_project_module(Path("project/v0.1.0/EPIC-001/FEAT-001"))
        mock_cache = mock_cache_module("abc123")
        with patch.dict(
            "sys.modules",
            {"release_plan.project": mock_proj, "utils.cache": mock_cache},
        ):
            item = {"filepath": "{project}/plans/final-plan_{session}.md"}
            deliverable = parse_deliverable(item, "read")

            regex = deliverable.regex_pattern
            current_path = "project/v0.1.0/EPIC-001/FEAT-001/plans/final-plan_abc123.md"
            other_feature = (
                "project/v0.1.0/EPIC-001/FEAT-002/plans/final-plan_abc123.md"
            )
            other_session = (
                "project/v0.1.0/EPIC-001/FEAT-001/plans/final-plan_xyz789.md"
            )

            assert re.match(regex, current_path)
            assert not re.match(regex, other_feature)
            assert not re.match(regex, other_session)

    def test_generic_pattern_matches_anywhere(self):
        """Test generic pattern (no placeholders) matches any location."""
        item = {"filepath": "src/**/*.ts"}
        deliverable = parse_deliverable(item, "edit")

        regex = deliverable.regex_pattern
        assert re.match(regex, "src/components/Button.ts")
        assert re.match(regex, "some/prefix/src/utils/helper.ts")
        assert re.match(regex, "project/v0.1.0/src/index.ts")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
