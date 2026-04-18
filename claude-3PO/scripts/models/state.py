"""Pydantic v2 schema for the workflow's persisted state.

Every model inherits from :class:`_Base`, which sets ``extra="allow"`` so that
older snapshots stored on disk in ``state.jsonl`` keep round-tripping after the
schema gains new fields. ``State`` is the top-level model — every other class
in this module is a nested sub-component referenced from one of its fields.
"""

from pydantic import BaseModel, ConfigDict
from typing import Literal


ReviewResult = Literal["Pass", "Fail"]

DONE_STATUSES: tuple[str, ...] = ("completed", "skipped")
"""Phase statuses that count as finished for auto-advance and completion checks."""

TDD_PHASES: tuple[str, ...] = ("write-tests", "test-review", "tests-review")
"""Phases that are skipped from workflow progression when TDD is disabled."""


class _Base(BaseModel):
    """Base model that tolerates unknown fields for forward-compat.

    All state models accept unknown keys so :func:`load` stays resilient to
    live ``state.jsonl`` snapshots that pre-date schema additions — adding a
    new field never invalidates the operator's existing on-disk state.

    Example:
        >>> _Base().model_config["extra"]
        'allow'
    """

    model_config = ConfigDict(extra="allow")


class PlanReview(_Base):
    """One iteration of a plan review (scores + pass/fail verdict).

    Example:
        >>> PlanReview(iteration=1, scores={"clarity": 8}, status="Pass").status
        'Pass'
    """

    iteration: int = 0
    scores: dict[str, int] | None = None
    status: ReviewResult | None = None


class CodeReview(_Base):
    """One iteration of a code review (scores + pass/fail verdict).

    Example:
        >>> CodeReview(iteration=2, scores={"correctness": 9}, status="Pass").iteration
        2
    """

    iteration: int = 0
    scores: dict[str, int] | None = None
    status: ReviewResult | None = None


class TestReview(_Base):
    """One iteration of a test review (binary verdict, no scoring).

    Example:
        >>> TestReview(verdict="Fail").verdict
        'Fail'
    """

    iteration: int = 0
    verdict: ReviewResult | None = None
    status: ReviewResult | None = None


class Task(_Base):
    """A project task tracked by the workflow.

    Nesting is flat: a subtask carries its ``parent_task_id`` rather than
    being stored inside its parent. That keeps state mutations local — any
    task can be appended, looked up, or updated without walking a tree.

    Example:
        >>> Task(task_id="T-1", subject="Build login").task_id
        'T-1'
    """

    task_id: str
    subject: str
    description: str | None = None
    parent_task_id: str | None = None


class Validation(_Base):
    """One validation result (binary pass/fail).

    Example:
        >>> Validation(result="pass").result
        'pass'
    """

    result: Literal["pass", "fail"]


class Plan(_Base):
    """The plan artifact for the current workflow.

    ``reviews`` is a *list* of :class:`PlanReview` (not a single review) — a
    recent schema change to support multi-iteration plan revision; downstream
    code should iterate or take the last entry rather than expecting a scalar.

    Example:
        >>> Plan(file_path="docs/plan.md", written=True).written
        True
    """

    file_path: str | None = None
    written: bool = False
    revised: bool | None = None
    reviews: list[PlanReview] = []


class Tests(_Base):
    """Test artifacts: which test files exist, ran, and need revision.

    Example:
        >>> Tests(file_paths=["tests/test_a.py"], executed=True).executed
        True
    """

    file_paths: list[str] = []
    executed: bool = False
    reviews: list[TestReview] = []
    files_to_revise: list[str] = []
    files_revised: list[str] = []


class CodeFiles(_Base):
    """Source files written this workflow plus their review/revision state.

    Example:
        >>> CodeFiles(file_paths=["src/foo.py"]).file_paths
        ['src/foo.py']
    """

    file_paths: list[str] = []
    reviews: list[CodeReview] = []
    tests_to_revise: list[str] = []
    tests_revised: list[str] = []
    files_to_revise: list[str] = []
    files_revised: list[str] = []


class PhaseEntry(_Base):
    """One entry in ``State.phases`` tracking the lifecycle of a phase.

    Example:
        >>> PhaseEntry(name="plan", status="completed").status
        'completed'
    """

    name: str
    status: Literal["in_progress", "completed", "skipped"] = "in_progress"


class Agent(_Base):
    """A subagent invocation (name, status, tool-use correlation id).

    Example:
        >>> Agent(name="planner", status="in_progress", tool_use_id="tu_1").name
        'planner'
    """

    name: str
    status: Literal["in_progress", "completed", "failed"] | None = None
    tool_use_id: str | None = None


class PR(_Base):
    """Pull-request state for the workflow output.

    Example:
        >>> PR(status="created", number=42).number
        42
    """

    status: Literal["pending", "created", "merged"] = "pending"
    number: int | None = None


class CI(_Base):
    """Continuous-integration state for the workflow's PR.

    Example:
        >>> CI(status="passed", results=[{"job": "lint", "ok": True}]).status
        'passed'
    """

    status: Literal["pending", "passed", "failed"] = "pending"
    results: list[dict] | None = None


class State(_Base):
    """Top-level workflow state persisted to ``state.jsonl``.

    A new line is appended each time any guard, hook, or agent mutates state;
    the latest line is the live snapshot. All sub-fields are nested ``_Base``
    models so the whole tree benefits from forward-compatible deserialization.

    Example:
        >>> State(session_id="s-1").workflow_active
        True
    """

    session_id: str
    workflow_active: bool = True
    status: Literal["in_progress", "completed"] | None = None
    workflow_type: str = "implement"
    phases: list[PhaseEntry] = []
    tdd: bool = False
    test_mode: bool | str | None = None
    story_id: str | None = None
    skip: list[str] = []
    instructions: str = ""
    agents: list[Agent] = []
    plan: Plan = Plan()
    tasks: list[str] = []
    project_tasks: list[Task] = []
    tests: Tests = Tests()
    code_files_to_write: list[str] = []
    code_files: CodeFiles = CodeFiles()
    quality_check_result: ReviewResult | None = None
    pr: PR = PR()
    ci: CI = CI()
    report_written: bool = False
    report_file_path: str | None = None
    plan_files_to_modify: list[str] = []
    commands: list[str] = []
    validations: list[Validation] = []
