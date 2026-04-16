"""Tests for validate_product_vision.py"""

import pytest

from validate_product_vision import validate


VALID_VISION_MD = """\
# Product Vision

**Project:** MyApp
**Version:** v1.0
**Author:** Jane Doe
**Last Updated:** 2026-04-16

---

## Vision Statement

> For developers who struggle with deployment, MyApp is a CLI tool that automates it.

---

## The Problem

### Who Has This Problem?

| Segment     | Description           | Size  |
| ----------- | --------------------- | ----- |
| Developers  | Ship code to prod     | 10M   |

### What's Broken Today?

Deploying takes too long and is error-prone.

### Why Now?

Cloud adoption has accelerated, making automated deployment essential.

---

## The Solution

### Product in One Paragraph

MyApp automates deployments with one command.

### Core Value Propositions

| #   | Value Proposition     | User Benefit       |
| --- | --------------------- | ------------------ |
| 1   | One-click deploy      | Save 2 hours/week  |

### How It Works (High Level)

```
Step 1: User runs deploy
Step 2: App builds
Step 3: App is live
```

---

## Market Landscape

### Competitive Positioning

| Competitor / Alternative | What They Do   | Their Weakness | Our Advantage  |
| ------------------------ | -------------- | -------------- | -------------- |
| Manual deploy            | SSH + scripts  | Slow           | Automated      |

### Defensibility

Deep integration with major cloud providers gives us a technical moat.

---

## Strategy

### MVP Scope

| Feature     | Why It's in MVP          |
| ----------- | ------------------------ |
| CLI deploy  | Core value proposition   |

### What's Explicitly NOT in MVP

| Excluded Feature | Why Not Yet           |
| ---------------- | --------------------- |
| GUI dashboard    | Not enough resources  |

### Product Roadmap (High Level)

| Phase   | Timeframe | Theme     | Key Outcomes     |
| ------- | --------- | --------- | ---------------- |
| MVP     | Q1 2026   | Core loop | Users can deploy |

---

## Business Model

### Revenue Model

| Model    | Description              |
| -------- | ------------------------ |
| Freemium | Free for 1 app, $10/mo  |

### Key Metrics

| Metric    | Definition               | MVP Target |
| --------- | ------------------------ | ---------- |
| DAU       | Daily active users       | 100        |

### Unit Economics (If Known)

| Metric | Value | Notes       |
| ------ | ----- | ----------- |
| CAC    | $5    | Organic     |

---

## Risks & Mitigations

| Risk         | Impact | Likelihood | Mitigation        |
| ------------ | ------ | ---------- | ----------------- |
| Low adoption | H      | M          | Beta user program |

---

## Team & Resources

| Role      | Who       | Status |
| --------- | --------- | ------ |
| Lead      | Jane Doe  | Active |

### Current Runway / Budget

Bootstrapped, 12 months runway.

---

## Success Criteria

### MVP Launch (Go / No-Go)

- [ ] 50 users complete deploy in first week
- [ ] Positive feedback from 10 target users

### 6-Month Vision

1000 active users deploying weekly.

### 12-Month Vision

Become the default deploy tool for indie developers.

---

## Appendix

### Glossary

| Term   | Definition             |
| ------ | ---------------------- |
| Deploy | Push code to prod      |

### References

- Internal user interviews (March 2026)

---

## Document History

| Version | Date       | Author   | Changes       |
| ------- | ---------- | -------- | ------------- |
| 1.0     | 2026-04-16 | Jane Doe | Initial draft |
"""


# ── Valid Input ──────────────────────────────────────────────────────────────


class TestValidInput:
    def test_valid_vision_has_no_errors(self):
        assert validate(VALID_VISION_MD) == []


# ── Metadata ─────────────────────────────────────────────────────────────────


class TestMetadataValidation:
    def test_missing_project(self):
        md = VALID_VISION_MD.replace("**Project:** MyApp", "")
        errors = validate(md)
        assert any("'Project'" in e for e in errors)

    def test_missing_version(self):
        md = VALID_VISION_MD.replace("**Version:** v1.0", "")
        errors = validate(md)
        assert any("'Version'" in e for e in errors)

    def test_missing_author(self):
        md = VALID_VISION_MD.replace("**Author:** Jane Doe", "")
        errors = validate(md)
        assert any("'Author'" in e for e in errors)

    def test_missing_last_updated(self):
        md = VALID_VISION_MD.replace("**Last Updated:** 2026-04-16", "")
        errors = validate(md)
        assert any("'Last Updated'" in e for e in errors)

    def test_placeholder_value(self):
        md = VALID_VISION_MD.replace("**Project:** MyApp", "**Project:** [Project Name]")
        errors = validate(md)
        assert any("placeholder" in e for e in errors)

    def test_empty_value(self):
        md = VALID_VISION_MD.replace("**Project:** MyApp", "**Project:**")
        errors = validate(md)
        assert any("empty" in e for e in errors)


# ── Sections ─────────────────────────────────────────────────────────────────


class TestSectionValidation:
    def test_missing_vision_statement(self):
        md = VALID_VISION_MD.replace("## Vision Statement", "## Something Else")
        errors = validate(md)
        assert any("'## Vision Statement'" in e for e in errors)

    def test_missing_the_problem(self):
        md = VALID_VISION_MD.replace("## The Problem", "## Problems")
        errors = validate(md)
        assert any("'## The Problem'" in e for e in errors)

    def test_missing_business_model(self):
        md = VALID_VISION_MD.replace("## Business Model", "## Money")
        errors = validate(md)
        assert any("'## Business Model'" in e for e in errors)

    def test_unknown_section_flagged(self):
        md = VALID_VISION_MD.replace("## Vision Statement", "## Vision Statement\n\n## Random Section")
        errors = validate(md)
        assert any("unknown section" in e and "Random Section" in e for e in errors)

    @pytest.mark.parametrize("section", [
        "Vision Statement", "The Problem", "The Solution",
        "Market Landscape", "Strategy", "Business Model",
        "Risks & Mitigations", "Team & Resources",
        "Success Criteria", "Appendix", "Document History",
    ])
    def test_each_required_section(self, section):
        md = VALID_VISION_MD.replace(f"## {section}", f"## REMOVED_{section}")
        errors = validate(md)
        assert any(section in e for e in errors)


# ── Subsections ──────────────────────────────────────────────────────────────


class TestSubsectionValidation:
    def test_missing_who_has_this_problem(self):
        md = VALID_VISION_MD.replace("### Who Has This Problem?", "### Wrong")
        errors = validate(md)
        assert any("Who Has This Problem?" in e for e in errors)

    def test_missing_whats_broken(self):
        md = VALID_VISION_MD.replace("### What's Broken Today?", "### Wrong")
        errors = validate(md)
        assert any("What's Broken Today?" in e for e in errors)

    def test_missing_why_now(self):
        md = VALID_VISION_MD.replace("### Why Now?", "### Wrong")
        errors = validate(md)
        assert any("Why Now?" in e for e in errors)

    def test_missing_product_in_one_paragraph(self):
        md = VALID_VISION_MD.replace("### Product in One Paragraph", "### Wrong")
        errors = validate(md)
        assert any("Product in One Paragraph" in e for e in errors)

    def test_missing_core_value_propositions(self):
        md = VALID_VISION_MD.replace("### Core Value Propositions", "### Wrong")
        errors = validate(md)
        assert any("Core Value Propositions" in e for e in errors)

    def test_missing_mvp_scope(self):
        md = VALID_VISION_MD.replace("### MVP Scope", "### Wrong")
        errors = validate(md)
        assert any("MVP Scope" in e for e in errors)

    def test_missing_competitive_positioning(self):
        md = VALID_VISION_MD.replace("### Competitive Positioning", "### Wrong")
        errors = validate(md)
        assert any("Competitive Positioning" in e for e in errors)

    def test_missing_glossary(self):
        md = VALID_VISION_MD.replace("### Glossary", "### Wrong")
        errors = validate(md)
        assert any("Glossary" in e for e in errors)

    def test_missing_mvp_launch(self):
        md = VALID_VISION_MD.replace("### MVP Launch (Go / No-Go)", "### Wrong")
        errors = validate(md)
        assert any("MVP Launch" in e for e in errors)

    def test_missing_6_month_vision(self):
        md = VALID_VISION_MD.replace("### 6-Month Vision", "### Wrong")
        errors = validate(md)
        assert any("6-Month Vision" in e for e in errors)

    def test_missing_12_month_vision(self):
        md = VALID_VISION_MD.replace("### 12-Month Vision", "### Wrong")
        errors = validate(md)
        assert any("12-Month Vision" in e for e in errors)


# ── Tables ───────────────────────────────────────────────────────────────────


class TestTableValidation:
    def test_missing_segment_table(self):
        md = VALID_VISION_MD.replace("| Segment", "| Seg_WRONG")
        errors = validate(md)
        assert any("Who Has This Problem?" in e and "Segment" in e for e in errors)

    def test_missing_value_proposition_table(self):
        md = VALID_VISION_MD.replace("| #   | Value Proposition", "| Num | VP_WRONG")
        errors = validate(md)
        assert any("Core Value Propositions" in e for e in errors)

    def test_missing_competitor_table(self):
        md = VALID_VISION_MD.replace("| Competitor / Alternative", "| Comp_WRONG")
        errors = validate(md)
        assert any("Competitive Positioning" in e for e in errors)

    def test_missing_feature_table(self):
        md = VALID_VISION_MD.replace("| Feature", "| Feat_WRONG").replace("| Excluded Feature", "| Excl_WRONG")
        errors = validate(md)
        assert any("MVP Scope" in e for e in errors)

    def test_missing_revenue_table(self):
        md = VALID_VISION_MD.replace("| Model    |", "| Mod_WRONG |")
        errors = validate(md)
        assert any("Revenue Model" in e for e in errors)

    def test_missing_metric_table(self):
        md = VALID_VISION_MD.replace("| Metric    |", "| Met_WRONG |").replace("| Metric |", "| Met_WRONG |")
        errors = validate(md)
        assert any("Key Metrics" in e for e in errors)

    def test_missing_risk_table(self):
        md = VALID_VISION_MD.replace("| Risk", "| Rsk_WRONG")
        errors = validate(md)
        assert any("Risks & Mitigations" in e for e in errors)

    def test_missing_role_table(self):
        md = VALID_VISION_MD.replace("| Role", "| Rl_WRONG")
        errors = validate(md)
        assert any("Team & Resources" in e for e in errors)

    def test_missing_document_history_table(self):
        md = VALID_VISION_MD.replace("| Version | Date", "| Ver_WRONG | Date")
        errors = validate(md)
        assert any("Document History" in e for e in errors)


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_content(self):
        errors = validate("")
        assert len(errors) > 0

    def test_multiple_errors_accumulated(self):
        errors = validate("# Product Vision\nNothing else here")
        metadata_errors = [e for e in errors if "metadata" in e]
        section_errors = [e for e in errors if "structure" in e]
        assert len(metadata_errors) >= 4
        assert len(section_errors) >= 11
