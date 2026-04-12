"""Tests validating that docs/architecture/decisions.md meets SK-001 acceptance criteria.

These tests enforce that the feature importance analysis documentation exists and contains
the required sections (DECISION-009) and feature set recommendations (DECISION-008).
"""

import os
import re
import pytest

DECISIONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "architecture", "decisions.md"
)


@pytest.fixture(scope="module")
def decisions_content():
    """Read decisions.md content once for all tests in this module."""
    with open(DECISIONS_PATH, "r") as f:
        return f.read()


class TestDecisionsFileExists:
    """Test that the decisions.md file is present."""

    def test_decisions_md_file_exists(self):
        """docs/architecture/decisions.md must exist."""
        assert os.path.isfile(DECISIONS_PATH), (
            f"decisions.md not found at {DECISIONS_PATH}"
        )

    def test_decisions_md_is_not_empty(self, decisions_content):
        """decisions.md must not be empty."""
        assert len(decisions_content.strip()) > 0


class TestDecision008FeatureSetRecommendations:
    """Test that DECISION-008 covers feature set recommendations with pros/cons (T-018)."""

    def test_decision_008_present(self, decisions_content):
        """DECISION-008 section must be present."""
        assert "DECISION-008" in decisions_content

    def test_combo_a_present(self, decisions_content):
        """Feature Set A (Basic) must be documented."""
        assert re.search(r"Combo\s*A|Set\s*A|Basic", decisions_content, re.IGNORECASE)

    def test_combo_b_present(self, decisions_content):
        """Feature Set B (Four Factors) must be documented."""
        assert re.search(
            r"Combo\s*B|Set\s*B|Four\s*Factor", decisions_content, re.IGNORECASE
        )

    def test_combo_c_present(self, decisions_content):
        """Feature Set C (Extended) must be documented."""
        assert re.search(
            r"Combo\s*C|Set\s*C|Extended", decisions_content, re.IGNORECASE
        )

    def test_pros_cons_documented(self, decisions_content):
        """Pros and/or cons must be documented within the DECISION-008 section."""
        after_d008 = decisions_content[decisions_content.find("DECISION-008"):]
        assert re.search(r"pros|cons|advantage|disadvantage|tradeoff|trade-off", after_d008, re.IGNORECASE)

    def test_expected_accuracy_ranges_present(self, decisions_content):
        """Accuracy ranges (e.g. 63-67%, 67-70%, 70-74%) must be present."""
        # Matches patterns like "63-67%" or "63–67%"
        assert re.search(r"6[0-9][–\-][0-9]{2}%", decisions_content), (
            "Expected accuracy ranges for feature combos not found in decisions.md"
        )

    def test_combo_c_recommended(self, decisions_content):
        """Combo C (Extended) must be documented as the recommended feature set."""
        forward_match = re.search(
            r"(recommend|production|best|preferred).{0,100}(Combo\s*C|Set\s*C|Extended)",
            decisions_content,
            re.IGNORECASE | re.DOTALL,
        )
        reverse_match = re.search(
            r"(Combo\s*C|Set\s*C|Extended).{0,100}(recommend|production|best|preferred)",
            decisions_content,
            re.IGNORECASE | re.DOTALL,
        )
        assert forward_match or reverse_match, (
            "Combo C is not documented as the recommended feature set in decisions.md"
        )


class TestDecision009FeatureImportanceAnalysis:
    """Test that DECISION-009 documents feature importance analysis (T-017)."""

    def test_decision_009_present(self, decisions_content):
        """DECISION-009 section must be present."""
        assert "DECISION-009" in decisions_content

    def test_top_10_features_documented(self, decisions_content):
        """At least 10 features must be individually listed in the decisions.md."""
        after_d009 = decisions_content[decisions_content.find("DECISION-009"):]
        # Match numbered list items: "1.", "2.", ..., "10." or table rows with rank numbers
        numbered_items = re.findall(
            r"(?:^|\|)\s*\d+\s*[\.\|]", after_d009, re.MULTILINE
        )
        unique_ranks = set(
            int(re.search(r"\d+", m).group()) for m in numbered_items
            if re.search(r"\d+", m)
        )
        assert len(unique_ranks) >= 10, (
            f"Expected at least 10 ranked features in DECISION-009, found {len(unique_ranks)}: {sorted(unique_ranks)}"
        )

    def test_shap_mentioned(self, decisions_content):
        """SHAP must be mentioned as the feature importance method."""
        assert re.search(r"\bSHAP\b", decisions_content, re.IGNORECASE)

    def test_efg_feature_present(self, decisions_content):
        """eFG% (effective field goal percentage) must appear in the feature list."""
        assert re.search(r"eFG|efg_pct|effective.field.goal", decisions_content, re.IGNORECASE)

    def test_net_rating_feature_present(self, decisions_content):
        """Net Rating must appear in the feature list."""
        assert re.search(r"net.?rat|net_rtg", decisions_content, re.IGNORECASE)

    def test_four_factors_referenced(self, decisions_content):
        """Dean Oliver's Four Factors must be referenced."""
        assert re.search(r"four.factor|Dean.Oliver", decisions_content, re.IGNORECASE)

    def test_adr_context_field_present(self, decisions_content):
        """DECISION-009 must have a Context field (standard ADR template)."""
        # Check for Context appearing after DECISION-009
        after_d009 = decisions_content[decisions_content.find("DECISION-009"):]
        assert re.search(r"##?\s*Context|Context\s*:", after_d009, re.IGNORECASE)

    def test_adr_alternatives_field_present(self, decisions_content):
        """DECISION-009 must have an Alternatives field (standard ADR template)."""
        after_d009 = decisions_content[decisions_content.find("DECISION-009"):]
        assert re.search(r"##?\s*Alternatives|Alternatives\s*:", after_d009, re.IGNORECASE)

    def test_adr_consequences_field_present(self, decisions_content):
        """DECISION-009 must have a Consequences field (standard ADR template)."""
        after_d009 = decisions_content[decisions_content.find("DECISION-009"):]
        assert re.search(r"##?\s*Consequences|Consequences\s*:", after_d009, re.IGNORECASE)

    def test_synthetic_data_limitation_documented(self, decisions_content):
        """Limitation about synthetic data must be documented in DECISION-009."""
        after_d009 = decisions_content[decisions_content.find("DECISION-009"):]
        assert re.search(r"synthetic|limitation|real\s*nba|production.data", after_d009, re.IGNORECASE)
