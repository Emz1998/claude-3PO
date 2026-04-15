"""resolvers.py — Backward-compatible wrappers for resolver classes.

Each public function delegates to PhaseResolver or ToolResolver.
External consumers import from here; the classes live in resolvers/*.
"""

from typing import Literal

from .state_store import StateStore
from config import Config

from resolvers.phase_resolver import PhaseResolver
from resolvers.tool_resolver import ToolResolver


def is_revision_needed(
    file_type: Literal["plan", "report", "tests", "code"],
    confidence_score: int,
    quality_score: int,
    config: Config,
) -> bool:
    """Check if scores meet threshold. Used by agent_report_guard."""
    r = PhaseResolver(config, StateStore.__new__(StateStore))
    return r._is_revision_needed(file_type, confidence_score, quality_score)


# ── Phase resolvers (reviews, agents) ─────────────────────────────

def resolve_plan_review(config: Config, state: StateStore) -> None:
    PhaseResolver(config, state)._resolve_plan_review()


def resolve_code_review(config: Config, state: StateStore) -> None:
    PhaseResolver(config, state)._resolve_code_review()


def resolve_test_review(config: Config, state: StateStore) -> None:
    PhaseResolver(config, state)._resolve_test_review()


def resolve_quality_check(state: StateStore) -> None:
    PhaseResolver(Config(), state)._resolve_quality_check()


def resolve_validate(state: StateStore) -> None:
    PhaseResolver(Config(), state)._resolve_validate()


def resolve_explore(config: Config, state: StateStore) -> None:
    PhaseResolver(config, state)._resolve_explore()


def resolve_research(config: Config, state: StateStore) -> None:
    PhaseResolver(config, state)._resolve_research()


# ── Tool resolvers (file writes, bash, tasks) ─────────────────────

def resolve_plan(config: Config, state: StateStore) -> None:
    ToolResolver(config, state)._resolve_plan()


def resolve_write_code(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_write_code()


def resolve_write_tests(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_write_tests()


def resolve_install_dependencies(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_install_deps()


def resolve_define_contracts(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_define_contracts()


def resolve_create_tasks(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_create_tasks()


def resolve_pr_create(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_pr_create()


def resolve_ci_check(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_ci_check()


def resolve_report(state: StateStore) -> None:
    ToolResolver(Config(), state)._resolve_report()


# ── Lifecycle ─────────────────────────────────────────────────────

def _auto_start_next(config: Config, state: StateStore, skip_checkpoint: bool = False) -> None:
    PhaseResolver(config, state).auto_start_next(skip_checkpoint)


def resolve(config: Config, state: StateStore) -> None:
    PhaseResolver(config, state).resolve()
