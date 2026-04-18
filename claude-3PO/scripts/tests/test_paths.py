"""Tests for utils/paths.py — shared path-matching helpers."""

import pytest

from lib.paths import basenames, path_matches


# ═══════════════════════════════════════════════════════════════════
# basenames
# ═══════════════════════════════════════════════════════════════════


class TestBasenames:
    def test_empty_list_returns_empty_set(self):
        assert basenames([]) == set()

    def test_absolute_paths(self):
        paths = ["/a/b/foo.py", "/c/d/bar.py"]
        assert basenames(paths) == {"foo.py", "bar.py"}

    def test_relative_paths(self):
        paths = ["src/foo.py", "tests/bar.py"]
        assert basenames(paths) == {"foo.py", "bar.py"}

    def test_mixed_extensions(self):
        paths = ["docs/plan.md", "state/state.jsonl", "src/a.py"]
        assert basenames(paths) == {"plan.md", "state.jsonl", "a.py"}

    def test_no_separator(self):
        assert basenames(["foo.py"]) == {"foo.py"}

    def test_duplicates_collapse(self):
        paths = ["/a/foo.py", "/b/foo.py"]
        assert basenames(paths) == {"foo.py"}

    def test_trailing_slash_yields_empty_name(self):
        # Documented behaviour: rsplit on trailing "/" leaves "" as the tail.
        assert basenames(["a/b/"]) == {""}


# ═══════════════════════════════════════════════════════════════════
# path_matches
# ═══════════════════════════════════════════════════════════════════


class TestPathMatches:
    @pytest.mark.parametrize(
        "file_path,expected,result",
        [
            ("docs/plan.md", "docs/plan.md", True),
            ("/repo/docs/plan.md", "docs/plan.md", True),
            ("docs/notes.md", "docs/plan.md", False),
            ("", "docs/plan.md", False),
            ("docs/plan.md", "", False),
        ],
    )
    def test_exact_and_suffix_matches(self, file_path, expected, result):
        assert path_matches(file_path, expected) is result

    def test_none_expected_is_false(self):
        assert path_matches("docs/plan.md", None) is False

    def test_both_none_is_false(self):
        assert path_matches("", None) is False

    def test_markdown_vs_json(self):
        assert path_matches("/r/a.md", "a.md") is True
        assert path_matches("/r/a.json", "a.md") is False

    def test_plan_vs_other_doc_suffix(self):
        assert path_matches("/r/docs/plan.md", "docs/plan.md") is True
        assert path_matches("/r/docs/notes.md", "docs/plan.md") is False
