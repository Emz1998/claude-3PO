from pydantic import BaseModel
from typing import Literal


ReviewResult = Literal["Pass", "Fail"]


class PlanReview(BaseModel):
    iteration: int = 0
    scores: dict[str, int] | None = None
    status: ReviewResult | None = None


class Plan(BaseModel):
    file_path: str | None = None
    written: bool = False
    review: PlanReview = PlanReview()


class Tests(BaseModel):
    file_paths: list[str] = []
    review_result: ReviewResult | None = None
    executed: bool = False


class CodeReview(BaseModel):
    iteration: int = 0
    scores: dict[str, int] | None = None
    status: ReviewResult | None = None


class CodeFiles(BaseModel):
    file_paths: list[str] = []
    review: CodeReview = CodeReview()


class PhaseEntry(BaseModel):
    name: str
    status: Literal["in_progress", "completed"] = "in_progress"


class Agent(BaseModel):
    name: str
    status: Literal["in_progress", "completed"] | None = None
    tool_use_id: str | None = None


class PR(BaseModel):
    status: Literal["pending", "created", "merged"] = "pending"
    number: int | None = None


class CI(BaseModel):
    status: Literal["pending", "passed", "failed"] = "pending"
    results: list[dict] | None = None


class Dependencies(BaseModel):
    packages: list[str] = []
    installed: bool = False


class Contracts(BaseModel):
    file_path: str | None = None
    names: list[str] = []
    code_files: list[str] = []
    written: bool = False
    validated: bool = False


class State(BaseModel):
    session_id: str
    workflow_active: bool = True
    workflow_type: str = "implement"
    phases: list[PhaseEntry] = []
    tdd: bool = False
    story_id: str | None = None
    skip: list[str] = []
    instructions: str = ""
    agents: list[Agent] = []
    plan: Plan = Plan()
    tasks: list[str] = []
    dependencies: Dependencies = Dependencies()
    contracts: Contracts = Contracts()
    tests: Tests = Tests()
    code_files_to_write: list[str] = []
    code_files: CodeFiles = CodeFiles()
    quality_check_result: ReviewResult | None = None
    pr: PR = PR()
    ci: CI = CI()
    report_written: bool = False
