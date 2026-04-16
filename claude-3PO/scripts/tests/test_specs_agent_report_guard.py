"""Tests for AgentReportGuard — architect and backlog phase handling."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from guardrails import STOP_GUARDS
from guardrails.agent_report_guard import AgentReportGuard

agent_report_guard = STOP_GUARDS["agent_report"]


class TestArchitectPhaseValidation:
    """AgentReportGuard should validate architecture content at SubagentStop."""

    def test_blocks_empty_report(self, config, state):
        state.add_phase("architect")
        hook = {"last_assistant_message": ""}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"

    def test_blocks_invalid_architecture(self, config, state):
        state.add_phase("architect")
        hook = {"last_assistant_message": "# Some random doc\n\nNo structure."}
        decision, msg = agent_report_guard(hook, config, state)
        assert decision == "block"
        assert "architect" in msg.lower() or "metadata" in msg.lower() or "structure" in msg.lower()

    def test_allows_valid_architecture_and_writes(self, config, state, tmp_path):
        state.add_phase("architect")
        content = _valid_architecture_md()
        hook = {"last_assistant_message": content}

        arch_path = str(tmp_path / "architecture.md")
        with patch("guardrails.agent_report_guard.Config") as MockConfig:
            mock_config = MagicMock()
            mock_config.architecture_file_path = arch_path
            decision, msg = AgentReportGuard(
                hook, mock_config, state
            ).validate()

        assert decision == "allow"


class TestBacklogPhaseValidation:
    """AgentReportGuard should validate backlog content at SubagentStop."""

    def test_blocks_empty_report(self, config, state):
        state.add_phase("backlog")
        hook = {"last_assistant_message": ""}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "block"

    def test_blocks_invalid_backlog(self, config, state):
        state.add_phase("backlog")
        hook = {"last_assistant_message": "# Random\n\nNo stories."}
        decision, msg = agent_report_guard(hook, config, state)
        assert decision == "block"

    def test_allows_valid_backlog_and_writes(self, config, state, tmp_path):
        state.add_phase("backlog")
        content = _valid_backlog_md()
        hook = {"last_assistant_message": content}

        md_path = str(tmp_path / "backlog.md")
        json_path = str(tmp_path / "backlog.json")
        with patch("guardrails.agent_report_guard.Config") as MockConfig:
            mock_config = MagicMock()
            mock_config.backlog_md_file_path = md_path
            mock_config.backlog_json_file_path = json_path
            decision, msg = AgentReportGuard(
                hook, mock_config, state
            ).validate()

        assert decision == "allow"


class TestAgentRetryAfterInvalidOutput:
    """Bug #6: failed specs agent must not count toward max, so retry is allowed."""

    def test_architect_failure_marks_agent_failed(self, config, state):
        from models.state import Agent

        state.add_phase("architect")
        state.add_agent(Agent(name="Architect", status="completed", tool_use_id="a-1"))
        hook = {"last_assistant_message": "# Broken\n\nNo structure."}

        decision, _ = agent_report_guard(hook, config, state)

        assert decision == "block"
        agents = state.agents
        assert any(
            a.get("name") == "Architect" and a.get("status") == "failed"
            for a in agents
        )

    def test_backlog_failure_marks_agent_failed(self, config, state):
        from models.state import Agent

        state.add_phase("backlog")
        state.add_agent(Agent(name="ProductOwner", status="completed", tool_use_id="po-1"))
        hook = {"last_assistant_message": "# Bad Backlog\n\nNo stories."}

        decision, _ = agent_report_guard(hook, config, state)

        assert decision == "block"
        agents = state.agents
        assert any(
            a.get("name") == "ProductOwner" and a.get("status") == "failed"
            for a in agents
        )

    def test_failed_agent_excluded_from_count(self, state):
        from models.state import Agent

        state.add_agent(Agent(name="Architect", status="failed", tool_use_id="a-1"))
        assert state.count_agents("Architect") == 0

    def test_active_agent_counted(self, state):
        from models.state import Agent

        state.add_agent(Agent(name="Architect", status="in_progress", tool_use_id="a-1"))
        state.add_agent(Agent(name="Architect", status="completed", tool_use_id="a-2"))
        assert state.count_agents("Architect") == 2


class TestNonSpecsPhases:
    """Existing phases should still work unchanged."""

    def test_plan_review_still_works(self, config, state):
        state.add_phase("plan-review")
        hook = {"last_assistant_message": "Confidence: 95\nQuality: 92"}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "allow"

    def test_quality_check_still_works(self, config, state):
        state.add_phase("quality-check")
        hook = {"last_assistant_message": "Pass"}
        decision, _ = agent_report_guard(hook, config, state)
        assert decision == "allow"


# ── Helpers ──────────────────────────────────────────────────────


def _valid_architecture_md() -> str:
    """Minimal valid architecture doc matching template structure."""
    sections = [
        "## 1. Project Overview",
        "### 1.1 Purpose & Business Context", "Content here",
        "### 1.2 Scope", "Content here",
        "### 1.3 Definitions & Acronyms", "Content here",
        "## 2. Architectural Decisions",
        "### 2.1 Architecture Style", "Monolith",
        "### 2.2 Key Architecture Decision Records (ADRs)", "ADR-1",
        "## 3. System Context & High-Level Architecture",
        "### 3.1 System Context", "Context",
        "### 3.2 Architecture Diagram", "Diagram",
        "## 4. System Components",
        "### 4.1 Project Structure Contract", "Contract",
        "### 4.2 Frontend Layer", "React",
        "### 4.3 API Layer", "REST",
        "### 4.4 Database Layer", "PostgreSQL",
        "### 4.5 Database Client Pattern", "Repository",
        "### 4.6 Migration Strategy", "Alembic",
        "### 4.7 Caching Strategy", "Redis",
        "### 4.8 Service Communication", "HTTP",
        "## 5. Data Flow & Integration Patterns",
        "### 5.1 Primary Request Flow", "Flow",
        "### 5.2 Asynchronous Flows", "Queue",
        "### 5.3 Third-Party Integrations", "Stripe",
        "### 5.4 Webhook Strategy", "Webhooks",
        "## 6. Security Architecture",
        "### 6.1 Authorization Model", "RBAC",
        "### 6.2 Authentication & Session Handling", "JWT",
        "### 6.3 API & Network Protection", "Rate limiting",
        "### 6.4 Data Protection & Secrets", "Vault",
        "### 6.5 Data Lifecycle", "Retention",
        "## 7. Testing Strategy", "Unit + Integration",
        "## 8. Observability",
        "### 8.1 Error Tracking", "Sentry",
        "### 8.2 Logging", "Structured",
        "### 8.3 Request Correlation", "Trace IDs",
        "### 8.4 Uptime & Alerting", "PagerDuty",
        "## 9. DevOps & Deployment",
        "### 9.1 Source Control & Branching", "Git flow",
        "### 9.2 Deployment", "Docker",
        "### 9.3 Environments", "Dev/Staging/Prod",
        "## 10. Reliability & Disaster Recovery", "Backups",
        "## 11. Cost & Operational Considerations",
        "### 11.1 Monthly Cost Estimate", "$500",
        "### 11.2 Scaling Cost Triggers", "10k users",
        "### 11.3 Vendor Lock-in Assessment", "Low",
        "## 12. Risks, Assumptions & Constraints",
        "### 12.1 Assumptions", "Stable APIs",
        "### 12.2 Constraints", "Budget limited",
        "### 12.3 Risks", "Timeline",
        "## 13. Appendix", "N/A",
    ]
    metadata = (
        "# Architecture\n\n"
        "**Project Name:** TestProject\n"
        "**Version:** 1.0\n"
        "**Date:** 2026-04-16\n"
        "**Author(s):** Test\n"
        "**Status:** Draft\n\n"
    )
    return metadata + "\n".join(sections)


def _valid_backlog_md() -> str:
    return (
        "# Backlog\n\n"
        "**Project:** Test\n"
        "**Last Updated:** 2026-04-16\n\n"
        "## Priority Legend\n\n"
        "## ID Conventions\n\n"
        "## Stories\n\n"
        "### US-001: First story\n\n"
        "> **As a** user, **I want** to test **so that** it works\n\n"
        "**Description:** A test story\n"
        "**Priority:** P0\n"
        "**Milestone:** MVP\n"
        "**Is Blocking:** None\n"
        "**Blocked By:** None\n\n"
        "- [ ] Acceptance criterion 1\n"
    )
