"""Tests for workflow/review/review.py"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from workflow.review.review import (
    resolve_file_name,
    resolve_report_file_path,
    extract_frontmatter,
    validate_report_file_path,
    validate_files_to_revise,
    validate_score,
    validate_report,
    build_review_prompt,
    review,
    MAX_REVIEW_DEPTH,
    REPORT_FILE_PATH,
)


# ---------------------------------------------------------------------------
# resolve_file_name
# ---------------------------------------------------------------------------


class TestResolveFileName:
    def test_plans_path_returns_plan_review(self):
        assert resolve_file_name("/project/plans/my-plan.md") == "plan-review"

    def test_py_file_returns_code_review(self):
        assert resolve_file_name("/src/app.py") == "code-review"

    def test_ts_file_returns_code_review(self):
        assert resolve_file_name("/src/component.ts") == "code-review"

    def test_test_py_file_returns_test_review(self):
        assert resolve_file_name("/src/app_test.py") == "test-review"

    def test_unknown_extension_returns_none(self):
        assert resolve_file_name("/docs/readme.md") is None

    def test_empty_path_returns_none(self):
        assert resolve_file_name("") is None


# ---------------------------------------------------------------------------
# resolve_report_file_path
# ---------------------------------------------------------------------------


class TestResolveReportFilePath:
    def test_returns_none_for_unrecognised_file(self):
        assert resolve_report_file_path("session-1", "/docs/readme.md") is None

    def test_code_file_builds_code_review_path(self):
        result = resolve_report_file_path("abc123", "/src/app.py")
        assert result is not None
        assert "abc123" in result
        assert "code-review" in result
        assert result.endswith(".md")

    def test_plan_file_builds_plan_review_path(self):
        result = resolve_report_file_path("abc123", "/project/plans/plan.md")
        assert result is not None
        assert "plan-review" in result

    def test_test_file_builds_test_review_path(self):
        result = resolve_report_file_path("abc123", "/src/app_test.py")
        assert result is not None
        assert "test-review" in result


# ---------------------------------------------------------------------------
# extract_frontmatter
# ---------------------------------------------------------------------------


class TestExtractFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nconfidence_score: 80\nquality_score: 75\n---\nBody text."
        result = extract_frontmatter(content)
        assert result == {"confidence_score": 80, "quality_score": 75}

    def test_no_frontmatter_returns_none(self):
        assert extract_frontmatter("Just plain text.") is None

    def test_empty_string_returns_none(self):
        assert extract_frontmatter("") is None

    def test_malformed_yaml_returns_none(self):
        # YAML that is syntactically invalid (tabs as indentation where not expected)
        content = "---\nkey: [unclosed\n---\nBody."
        assert extract_frontmatter(content) is None

    def test_frontmatter_with_list(self):
        content = "---\nfiles_to_revise:\n  - /src/a.py\n  - /src/b.py\n---"
        result = extract_frontmatter(content)
        assert result["files_to_revise"] == ["/src/a.py", "/src/b.py"]

    def test_leading_whitespace_is_tolerated(self):
        content = "\n\n---\nconfidence_score: 90\n---\n"
        result = extract_frontmatter(content)
        assert result == {"confidence_score": 90}


# ---------------------------------------------------------------------------
# validate_report_file_path
# ---------------------------------------------------------------------------


class TestValidateReportFilePath:
    def test_matching_path_is_valid(self):
        expected = resolve_report_file_path("sid", "/src/app.py")
        valid, msg = validate_report_file_path(expected, "sid", "/src/app.py")
        assert valid is True

    def test_wrong_path_is_invalid(self):
        valid, msg = validate_report_file_path("/wrong/path.md", "sid", "/src/app.py")
        assert valid is False
        assert "expected file path" in msg

    def test_error_message_contains_expected_path(self):
        expected = resolve_report_file_path("sid", "/src/app.py")
        _, msg = validate_report_file_path("/wrong.md", "sid", "/src/app.py")
        assert expected in msg


# ---------------------------------------------------------------------------
# validate_files_to_revise
# ---------------------------------------------------------------------------


class TestValidateFilesToRevise:
    def test_not_a_list_is_invalid(self):
        valid, msg = validate_files_to_revise("not-a-list")
        assert valid is False
        assert "list" in msg

    def test_empty_list_is_invalid(self):
        valid, msg = validate_files_to_revise([])
        assert valid is False
        assert "missing" in msg

    def test_non_existent_file_is_invalid(self):
        valid, msg = validate_files_to_revise(["/no/such/file.py"])
        assert valid is False
        assert "/no/such/file.py" in msg

    def test_existing_file_is_valid(self, tmp_path):
        f = tmp_path / "real.py"
        f.touch()
        valid, _ = validate_files_to_revise([str(f)])
        assert valid is True

    def test_mix_of_existing_and_missing_is_invalid(self, tmp_path):
        existing = tmp_path / "exists.py"
        existing.touch()
        valid, msg = validate_files_to_revise([str(existing), "/missing.py"])
        assert valid is False
        assert "/missing.py" in msg


# ---------------------------------------------------------------------------
# validate_score
# ---------------------------------------------------------------------------


class TestValidateScore:
    def test_none_score_is_invalid(self):
        valid, msg = validate_score("confidence_score", None)
        assert valid is False
        assert "missing" in msg

    def test_string_score_is_invalid(self):
        valid, msg = validate_score("quality_score", "high")
        assert valid is False
        assert "integer" in msg

    def test_score_below_range_is_invalid(self):
        valid, msg = validate_score("confidence_score", -1)
        assert valid is False
        assert "0 and 100" in msg

    def test_score_above_range_is_invalid(self):
        valid, msg = validate_score("quality_score", 101)
        assert valid is False

    def test_boundary_zero_is_valid(self):
        valid, _ = validate_score("confidence_score", 0)
        assert valid is True

    def test_boundary_100_is_valid(self):
        valid, _ = validate_score("quality_score", 100)
        assert valid is True

    def test_mid_range_score_is_valid(self):
        valid, _ = validate_score("confidence_score", 75)
        assert valid is True


# ---------------------------------------------------------------------------
# validate_report
# ---------------------------------------------------------------------------


class TestValidateReport:
    def test_none_frontmatter_is_invalid(self):
        valid, msg = validate_report(None)
        assert valid is False
        assert "Frontmatter" in msg

    def test_missing_all_fields_is_invalid(self):
        valid, msg = validate_report({})
        assert valid is False

    def test_collects_all_errors(self, tmp_path):
        # confidence_score missing, quality_score missing, files_to_revise missing
        valid, msg = validate_report({})
        assert valid is False
        assert "confidence_score" in msg
        assert "quality_score" in msg

    def test_valid_frontmatter_passes(self, tmp_path):
        f = tmp_path / "src.py"
        f.touch()
        valid, msg = validate_report(
            {
                "confidence_score": 80,
                "quality_score": 75,
                "files_to_revise": [str(f)],
            }
        )
        assert valid is True


# ---------------------------------------------------------------------------
# build_review_prompt
# ---------------------------------------------------------------------------


class TestBuildReviewPrompt:
    def test_includes_file_path(self):
        prompt = build_review_prompt("/src/app.py")
        assert "/src/app.py" in prompt

    def test_mentions_required_frontmatter_fields(self):
        prompt = build_review_prompt("/src/app.py")
        assert "confidence_score" in prompt
        assert "quality_score" in prompt
        assert "files_to_revise" in prompt


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------


def _make_response(text: str, session_id: str = "claude-sid") -> dict:
    return {"session_id": session_id, "result": text}


def _valid_report_text(files: list[str]) -> str:
    files_yaml = "\n".join(f"  - {f}" for f in files)
    return (
        f"---\nconfidence_score: 85\nquality_score: 80\nfiles_to_revise:\n{files_yaml}\n---\n\nLooks good."
    )


class TestReview:
    def test_valid_report_returned_immediately(self, tmp_path):
        f = tmp_path / "src.py"
        f.touch()
        report_text = _valid_report_text([str(f)])

        with patch(
            "workflow.review.review.run_reviewer",
            return_value=_make_response(report_text),
        ):
            result = review("Review this file.")

        assert result == report_text

    def test_retries_when_frontmatter_missing(self, tmp_path):
        f = tmp_path / "src.py"
        f.touch()
        valid_text = _valid_report_text([str(f)])

        responses = [
            _make_response("No frontmatter here."),
            _make_response(valid_text),
        ]

        with patch(
            "workflow.review.review.run_reviewer", side_effect=responses
        ) as mock_run:
            result = review("Review this file.")

        assert mock_run.call_count == 2
        assert result == valid_text

    def test_retries_when_validation_fails(self, tmp_path):
        f = tmp_path / "src.py"
        f.touch()
        valid_text = _valid_report_text([str(f)])

        # First response has out-of-range scores
        invalid_text = (
            f"---\nconfidence_score: 200\nquality_score: 80\n"
            f"files_to_revise:\n  - {f}\n---\nBody."
        )

        responses = [
            _make_response(invalid_text),
            _make_response(valid_text),
        ]

        with patch("workflow.review.review.run_reviewer", side_effect=responses):
            result = review("Review this file.")

        assert result == valid_text

    def test_raises_after_max_depth(self):
        with patch(
            "workflow.review.review.run_reviewer",
            return_value=_make_response("No frontmatter."),
        ):
            with pytest.raises(RuntimeError, match="Maximum review retry depth"):
                review("Review this file.")

    def test_passes_session_id_to_run_reviewer(self, tmp_path):
        f = tmp_path / "src.py"
        f.touch()
        valid_text = _valid_report_text([str(f)])

        with patch(
            "workflow.review.review.run_reviewer",
            return_value=_make_response(valid_text),
        ) as mock_run:
            review("Review this file.", session_id="my-session")

        mock_run.assert_called_once_with("Review this file.", "my-session")

    def test_resumes_with_claude_session_id_on_retry(self, tmp_path):
        f = tmp_path / "src.py"
        f.touch()
        valid_text = _valid_report_text([str(f)])

        responses = [
            _make_response("No frontmatter.", session_id="claude-sid-1"),
            _make_response(valid_text, session_id="claude-sid-2"),
        ]

        with patch(
            "workflow.review.review.run_reviewer", side_effect=responses
        ) as mock_run:
            review("Review this file.")

        # Second call must resume with the session_id returned by the first call
        _, retry_session_id, *_ = mock_run.call_args_list[1][0]
        assert retry_session_id == "claude-sid-1"
