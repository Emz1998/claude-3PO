"""Tests for specs workflow phase resolvers."""

import pytest
from models.state import Agent
from utils.resolver import Resolver, resolve


class TestResolveVision:
    def test_completes_when_doc_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        state.specs.set_doc_written("product_vision", True)
        state.specs.set_doc_path("product_vision", "projects/docs/product-vision.md")
        Resolver(config, state)._resolve_doc_phase("vision", "product_vision")
        assert state.is_phase_completed("vision")

    def test_does_not_complete_when_not_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        Resolver(config, state)._resolve_doc_phase("vision", "product_vision")
        assert not state.is_phase_completed("vision")


class TestResolveStrategy:
    def test_completes_when_all_agents_done(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("strategy")
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-1"))
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-2"))
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-3"))
        Resolver(config, state)._resolve_agent_phase("strategy")
        assert state.is_phase_completed("strategy")

    def test_does_not_complete_with_agent_in_progress(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("strategy")
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-1"))
        state.add_agent(Agent(name="Research", status="in_progress", tool_use_id="r-2"))
        Resolver(config, state)._resolve_agent_phase("strategy")
        assert not state.is_phase_completed("strategy")


class TestResolveDecision:
    def test_completes_when_doc_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("decision")
        state.specs.set_doc_written("decisions", True)
        state.specs.set_doc_path("decisions", "projects/docs/decisions.md")
        Resolver(config, state)._resolve_doc_phase("decision", "decisions")
        assert state.is_phase_completed("decision")

    def test_does_not_complete_when_not_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("decision")
        Resolver(config, state)._resolve_doc_phase("decision", "decisions")
        assert not state.is_phase_completed("decision")


class TestResolveArchitect:
    def test_completes_when_doc_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("architect")
        state.specs.set_doc_written("architecture", True)
        state.specs.set_doc_path("architecture", "projects/docs/architecture.md")
        Resolver(config, state)._resolve_doc_phase("architect", "architecture")
        assert state.is_phase_completed("architect")

    def test_does_not_complete_when_not_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("architect")
        Resolver(config, state)._resolve_doc_phase("architect", "architecture")
        assert not state.is_phase_completed("architect")


class TestResolveBacklog:
    def test_completes_when_doc_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("backlog")
        state.specs.set_doc_written("backlog", True)
        state.specs.set_doc_path("backlog", "projects/docs/backlog.md")
        Resolver(config, state)._resolve_doc_phase("backlog", "backlog")
        assert state.is_phase_completed("backlog")

    def test_does_not_complete_when_not_written(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("backlog")
        Resolver(config, state)._resolve_doc_phase("backlog", "backlog")
        assert not state.is_phase_completed("backlog")


class TestSpecsDispatch:
    def test_dispatches_vision_resolver(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("vision")
        state.specs.set_doc_written("product_vision", True)
        state.specs.set_doc_path("product_vision", "projects/docs/product-vision.md")
        resolve(config, state)
        assert state.is_phase_completed("vision")

    def test_dispatches_strategy_resolver(self, config, state):
        state.set("workflow_type", "specs")
        state.add_phase("strategy")
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-1"))
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-2"))
        state.add_agent(Agent(name="Research", status="completed", tool_use_id="r-3"))
        resolve(config, state)
        assert state.is_phase_completed("strategy")


class TestSpecsWorkflowCompletion:
    def test_completes_when_all_phases_done(self, config, state):
        state.set("workflow_type", "specs")
        for phase in ("vision", "strategy", "decision", "architect", "backlog"):
            state.add_phase(phase)
            state.set_phase_completed(phase)
        # Mark all docs written
        state.specs.set_doc_written("product_vision", True)
        state.specs.set_doc_written("decisions", True)
        state.specs.set_doc_written("architecture", True)
        state.specs.set_doc_written("backlog", True)
        resolve(config, state)
        assert state.get("status") == "completed"
        assert state.get("workflow_active") is False
