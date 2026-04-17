"""Tests for lib/scoring.py — score and verdict validation."""

import pytest

from lib.scoring import scores_valid, verdict_valid


# ── scores_valid ──────────────────────────────────────────────


class TestScoresValid:
    def test_valid_returns_true_with_scores(self):
        ok, data = scores_valid(
            "x", lambda _: {"confidence_score": 80, "quality_score": 90}
        )
        assert ok is True
        assert data == {"confidence_score": 80, "quality_score": 90}

    def test_missing_confidence_raises(self):
        with pytest.raises(ValueError, match="required"):
            scores_valid(
                "x", lambda _: {"confidence_score": None, "quality_score": 80}
            )

    def test_missing_quality_raises(self):
        with pytest.raises(ValueError, match="required"):
            scores_valid(
                "x", lambda _: {"confidence_score": 80, "quality_score": None}
            )

    def test_out_of_range_confidence_raises(self):
        with pytest.raises(ValueError, match="Confidence"):
            scores_valid(
                "x", lambda _: {"confidence_score": 101, "quality_score": 80}
            )

    def test_out_of_range_quality_raises(self):
        with pytest.raises(ValueError, match="Quality"):
            scores_valid(
                "x", lambda _: {"confidence_score": 80, "quality_score": 0}
            )


# ── verdict_valid ─────────────────────────────────────────────


class TestVerdictValid:
    @pytest.mark.parametrize("v", ["Pass", "Fail"])
    def test_valid_verdicts(self, v):
        ok, value = verdict_valid("x", lambda _: v)
        assert ok is True
        assert value == v

    @pytest.mark.parametrize("v", ["", "passed", "FAIL", "Maybe"])
    def test_invalid_verdicts(self, v):
        with pytest.raises(ValueError, match="Pass.*Fail"):
            verdict_valid("x", lambda _: v)
