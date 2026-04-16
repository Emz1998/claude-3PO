"""Tests for ask_user_question hook."""

from pathlib import Path

import pytest

from ask_user_question import (  # type: ignore
    load_approved_questions,
    validate_questions,
)


QUESTIONS_MD = Path(__file__).resolve().parent.parent.parent / "questions.md"

APPROVED_QUESTIONS = [
    "What is the name of your project and who is building it?",
    "Who are your target users and what problem do they face today?",
    "What has changed recently that makes now the right time to solve this problem?",
    "In one paragraph, what does your product do and how does it work at a high level?",
    "What are your top 3 value propositions and the user benefit of each?",
    "Who are your main competitors or alternatives, and what is your advantage over them?",
    "What features are in your MVP and what is explicitly excluded?",
    "What is your revenue model and what key metrics will you track?",
    "Who is on your team and what is your current runway or budget?",
    "What does success look like at MVP launch, 6 months, and 12 months?",
]


# ── Load Questions ───────────────────────────────────────────────────────────


class TestLoadApprovedQuestions:
    def test_loads_from_questions_md(self):
        questions = load_approved_questions(QUESTIONS_MD)
        assert len(questions) == 10
        assert questions[0] == APPROVED_QUESTIONS[0]
        assert questions[9] == APPROVED_QUESTIONS[9]

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_approved_questions(tmp_path / "nonexistent.md") == []

    def test_file_with_no_numbered_items(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("# No questions here\nJust text.")
        assert load_approved_questions(f) == []


# ── Validate Questions ───────────────────────────────────────────────────────


class TestValidateQuestions:
    def test_all_approved_returns_empty(self):
        assert validate_questions(APPROVED_QUESTIONS, APPROVED_QUESTIONS) == []

    def test_single_approved(self):
        assert validate_questions([APPROVED_QUESTIONS[0]], APPROVED_QUESTIONS) == []

    def test_unapproved_returned(self):
        rejected = validate_questions(["What is your favorite color?"], APPROVED_QUESTIONS)
        assert rejected == ["What is your favorite color?"]

    def test_mixed_only_rejects_bad(self):
        asked = [APPROVED_QUESTIONS[0], "Do you like pizza?"]
        rejected = validate_questions(asked, APPROVED_QUESTIONS)
        assert rejected == ["Do you like pizza?"]
        assert APPROVED_QUESTIONS[0] not in rejected

    def test_slightly_altered_rejected(self):
        rejected = validate_questions(["What is the name of your project?"], APPROVED_QUESTIONS)
        assert len(rejected) == 1

    def test_empty_asked_returns_empty(self):
        assert validate_questions([], APPROVED_QUESTIONS) == []

    def test_multiple_unapproved_all_returned(self):
        bad = ["Random question 1?", "Random question 2?"]
        rejected = validate_questions(bad, APPROVED_QUESTIONS)
        assert "Random question 1?" in rejected
        assert "Random question 2?" in rejected

    def test_subset_of_four_approved(self):
        assert validate_questions(APPROVED_QUESTIONS[:4], APPROVED_QUESTIONS) == []

    def test_empty_approved_rejects_all(self):
        rejected = validate_questions(["Any question?"], [])
        assert rejected == ["Any question?"]
