from pydantic import BaseModel, ConfigDict
from typing import Literal


ReviewResult = Literal["Pass", "Fail"]


class _Base(BaseModel):
    """All state models accept unknown keys to keep load() resilient
    to live state.jsonl snapshots that pre-date schema additions."""

    model_config = ConfigDict(extra="allow")


class PlanReview(_Base):
    iteration: int = 0
    scores: dict[str, int] | None = None
    status: ReviewResult | None = None


class CodeReview(_Base):
    iteration: int = 0
    scores: dict[str, int] | None = None
    status: ReviewResult | None = None


class TestReview(_Base):
    verdict: ReviewResult | None = None


class Plan(_Base):
    file_path: str | None = None
    written: bool = False
    revised: bool | None = None
    reviews: list[PlanReview] = []


class Tests(_Base):
    file_paths: list[str] = []
    executed: bool = False
    reviews: list[TestReview] = []
    files_to_revise: list[str] = []
    files_revised: list[str] = []


class CodeFiles(_Base):
    file_paths: list[str] = []
    reviews: list[CodeReview] = []
    tests_to_revise: list[str] = []
    tests_revised: list[str] = []
    files_to_revise: list[str] = []
    files_revised: list[str] = []


class PhaseEntry(_Base):
    name: str
    status: Literal["in_progress", "completed"] = "in_progress"


class Agent(_Base):
    name: str
    status: Literal["in_progress", "completed", "failed"] | None = None
    tool_use_id: str | None = None


class PR(_Base):
    status: Literal["pending", "created", "merged"] = "pending"
    number: int | None = None


class CI(_Base):
    status: Literal["pending", "passed", "failed"] = "pending"
    results: list[dict] | None = None


class Dependencies(_Base):
    packages: list[str] = []
    installed: bool = False


class Contracts(_Base):
    file_path: str | None = None
    names: list[str] = []
    code_files: list[str] = []
    written: bool = False
    validated: bool = False


class State(_Base):
    session_id: str
    workflow_active: bool = True
    status: Literal["in_progress", "completed"] | None = None
    workflow_type: str = "implement"
    phases: list[PhaseEntry] = []
    tdd: bool = False
    story_id: str | None = None
    skip: list[str] = []
    instructions: str = ""
    agents: list[Agent] = []
    plan: Plan = Plan()
    tasks: list[str] = []
    project_tasks: list[dict] = []
    dependencies: Dependencies = Dependencies()
    contracts: Contracts = Contracts()
    tests: Tests = Tests()
    code_files_to_write: list[str] = []
    code_files: CodeFiles = CodeFiles()
    quality_check_result: ReviewResult | None = None
    pr: PR = PR()
    ci: CI = CI()
    report_written: bool = False
    plan_files_to_modify: list[str] = []
