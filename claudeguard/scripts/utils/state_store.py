"""StateStore — JSON state with file-locking."""

import json
from pathlib import Path
from typing import Any, Callable, Literal

from models.state import Agent, State, ReviewResult
from .file_manager import FileManager


class StateStore:
    def __init__(self, state_path: Path, default_state: dict[str, Any] | None = None):
        self._path = state_path
        self._default_state = default_state or {}
        self._fm = FileManager(self._path, lock=True)

    # ── Core I/O ───────────────────────────────────────────────────

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return dict(self._default_state)
        return self._fm.load_file()

    def save(self, state: dict[str, Any] | None = None) -> None:
        self._fm.save_file(state)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:
        def _seeded(data: dict) -> None:
            if not data and self._default_state:
                data.update(self._default_state)
            fn(data)

        self._fm.update_file(_seeded)

    def get(self, key: str, default: Any = None) -> Any:
        data = self.load()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.update(lambda d: d.update({key: value}))

    def reset(self, default_state: dict[str, Any] | None = None) -> None:
        self._fm.save_file(default_state or {})

    def reinitialize(self, initial_state: dict[str, Any]) -> None:
        self._fm.save_file(initial_state)

    def delete(self) -> None:
        self._path.unlink(missing_ok=True)

    def archive(self, history_path: Path) -> None:
        """Append current state as a JSONL entry to history_path."""
        entry = json.dumps(self.load()) + "\n"
        with open(history_path, "a") as f:
            f.write(entry)

    @staticmethod
    def latest_from_history(history_path: Path) -> dict[str, Any] | None:
        """Return the last archived entry or None."""
        history_fm = FileManager(history_path, lock=True)
        entries = history_fm.load_file()
        if not entries:
            return None
        return entries[-1] if isinstance(entries, list) else None

    # ── Phases ─────────────────────────────────────────────────────

    @property
    def phases(self) -> list[dict]:
        return self.load().get("phases", [])

    @property
    def current_phase(self) -> str:
        """Current phase is the last item in the phases list."""
        phases = self.phases
        return phases[-1]["name"] if phases else ""

    def add_phase(self, name: str) -> None:
        def _add(d: dict) -> None:
            phases = d.get("phases", [])
            phases.append({"name": name, "status": "in_progress"})
            d["phases"] = phases

        self.update(_add)

    def complete_phase(self, name: str) -> None:
        def _complete(d: dict) -> None:
            phases = d.get("phases", [])
            for p in phases:
                if p["name"] == name:
                    p["status"] = "completed"
                    break

        self.update(_complete)

    def is_phase_completed(self, name: str) -> bool:
        return any(
            p["name"] == name and p["status"] == "completed" for p in self.phases
        )

    def get_phase_status(self, name: str) -> str | None:
        for p in self.phases:
            if p["name"] == name:
                return p["status"]
        return None

    # ── Sub-phases ─────────────────────────────────────────────────

    # ── Plan revision tracking ──────────────────────────────────────

    @property
    def plan_revised(self) -> bool:
        return self.load().get("plan", {}).get("revised", False)

    def set_plan_revised(self, revised: bool) -> None:
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["revised"] = revised

        self.update(_set)

    # ── Code revision tracking ────────────────────────────────────

    @property
    def files_to_revise(self) -> list[str]:
        return self.load().get("code_files", {}).get("files_to_revise", [])

    def set_files_to_revise(self, files: list[str]) -> None:
        def _set(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            cf["files_to_revise"] = files
            cf["files_revised"] = []

        self.update(_set)

    @property
    def files_revised(self) -> list[str]:
        return self.load().get("code_files", {}).get("files_revised", [])

    def add_file_revised(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            revised = cf.setdefault("files_revised", [])
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    @property
    def all_files_revised(self) -> bool:
        to_revise = set(self.files_to_revise)
        revised = set(self.files_revised)
        return bool(to_revise) and not (to_revise - revised)

    # ── Code review: test revision tracking (TDD) ─────────────────

    @property
    def code_tests_to_revise(self) -> list[str]:
        return self.load().get("code_files", {}).get("tests_to_revise", [])

    def set_code_tests_to_revise(self, files: list[str]) -> None:
        def _set(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            cf["tests_to_revise"] = files
            cf["tests_revised"] = []

        self.update(_set)

    @property
    def code_tests_revised(self) -> list[str]:
        return self.load().get("code_files", {}).get("tests_revised", [])

    def add_code_test_revised(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            revised = cf.setdefault("tests_revised", [])
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    @property
    def all_code_tests_revised(self) -> bool:
        to_revise = set(self.code_tests_to_revise)
        revised = set(self.code_tests_revised)
        return bool(to_revise) and not (to_revise - revised)

    # ── Agents ─────────────────────────────────────────────────────

    @property
    def agents(self) -> list[dict]:
        return self.load().get("agents", [])

    def add_agent(self, agent: Agent) -> None:
        def _add(d: dict) -> None:
            agents = d.get("agents", [])
            agents.append(agent.model_dump())
            d["agents"] = agents

        self.update(_add)

    def get_agent(self, name: str) -> dict[str, Any] | None:
        agents = self.agents
        return next((a for a in agents if a.get("name") == name), None)

    def count_agents(self, name: str) -> int:
        return sum(1 for a in self.agents if a.get("name") == name)

    def update_agent_status(
        self, agent_id: str, status: Literal["in_progress", "completed"]
    ) -> None:
        def _update(d: dict) -> None:
            agents = d.get("agents", [])
            agent = next(
                (a for a in agents if a.get("tool_use_id") == agent_id),
                None,
            )
            if agent:
                agent["status"] = status

        self.update(_update)

    # ── Plan ───────────────────────────────────────────────────────

    @property
    def plan(self) -> dict[str, Any]:
        return self.load().get("plan", {})

    def set_plan_file_path(self, file_path: str) -> None:
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["file_path"] = file_path

        self.update(_set)

    def set_plan_written(self, written: bool = True) -> None:
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["written"] = written

        self.update(_set)

    def add_plan_review(
        self,
        scores: dict[Literal["confidence_score", "quality_score"], int],
    ) -> None:
        def _add(d: dict) -> None:
            plan = d.setdefault("plan", {})
            reviews = plan.setdefault("reviews", [])
            reviews.append({"scores": scores, "status": None})

        self.update(_add)

    def set_last_plan_review_status(self, status: ReviewResult) -> None:
        def _set(d: dict) -> None:
            reviews = d.get("plan", {}).get("reviews", [])
            if reviews:
                reviews[-1]["status"] = status

        self.update(_set)

    @property
    def plan_reviews(self) -> list[dict]:
        return self.load().get("plan", {}).get("reviews", [])

    @property
    def plan_review_count(self) -> int:
        return len(self.plan_reviews)

    @property
    def last_plan_review(self) -> dict | None:
        reviews = self.plan_reviews
        return reviews[-1] if reviews else None

    # ── Tests ──────────────────────────────────────────────────────

    @property
    def tests(self) -> dict[str, Any]:
        return self.load().get("tests", {})

    def add_test_file(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            paths = tests.setdefault("file_paths", [])
            if file_path not in paths:
                paths.append(file_path)

        self.update(_add)

    def add_test_review(self, verdict: str) -> None:
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            reviews = tests.setdefault("reviews", [])
            reviews.append({"verdict": verdict})

        self.update(_add)

    @property
    def test_reviews(self) -> list[dict]:
        return self.load().get("tests", {}).get("reviews", [])

    @property
    def test_review_count(self) -> int:
        return len(self.test_reviews)

    @property
    def last_test_review(self) -> dict | None:
        reviews = self.test_reviews
        return reviews[-1] if reviews else None

    def set_tests_executed(self, executed: bool = True) -> None:
        def _set(d: dict) -> None:
            d.setdefault("tests", {})["executed"] = executed

        self.update(_set)

    # ── Test revision tracking ────────────────────────────────────

    @property
    def test_files_to_revise(self) -> list[str]:
        return self.load().get("tests", {}).get("files_to_revise", [])

    def set_test_files_to_revise(self, files: list[str]) -> None:
        def _set(d: dict) -> None:
            tests = d.setdefault("tests", {})
            tests["files_to_revise"] = files
            tests["files_revised"] = []

        self.update(_set)

    @property
    def test_files_revised(self) -> list[str]:
        return self.load().get("tests", {}).get("files_revised", [])

    def add_test_file_revised(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            revised = tests.setdefault("files_revised", [])
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    @property
    def all_test_files_revised(self) -> bool:
        to_revise = set(self.test_files_to_revise)
        revised = set(self.test_files_revised)
        return bool(to_revise) and not (to_revise - revised)

    # ── Code files to write ──────────────────────────────────────────

    @property
    def code_files_to_write(self) -> list[str]:
        return self.load().get("code_files_to_write", [])

    def add_code_file_to_write(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            paths = d.get("code_files_to_write", [])
            if file_path not in paths:
                paths.append(file_path)
            d["code_files_to_write"] = paths

        self.update(_add)

    # ── Code files ─────────────────────────────────────────────────

    @property
    def code_files(self) -> dict[str, Any]:
        return self.load().get("code_files", {})

    def add_code_file(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            paths = cf.setdefault("file_paths", [])
            if file_path not in paths:
                paths.append(file_path)

        self.update(_add)

    def add_code_review(
        self,
        scores: dict[Literal["confidence_score", "quality_score"], int],
    ) -> None:
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            reviews = cf.setdefault("reviews", [])
            reviews.append({"scores": scores, "status": None})

        self.update(_add)

    def set_last_code_review_status(self, status: ReviewResult) -> None:
        def _set(d: dict) -> None:
            reviews = d.get("code_files", {}).get("reviews", [])
            if reviews:
                reviews[-1]["status"] = status

        self.update(_set)

    @property
    def code_reviews(self) -> list[dict]:
        return self.load().get("code_files", {}).get("reviews", [])

    @property
    def code_review_count(self) -> int:
        return len(self.code_reviews)

    @property
    def last_code_review(self) -> dict | None:
        reviews = self.code_reviews
        return reviews[-1] if reviews else None

    # ── Quality check ──────────────────────────────────────────────

    @property
    def quality_check_result(self) -> str | None:
        return self.load().get("quality_check_result")

    def set_quality_check_result(self, result: ReviewResult) -> None:
        self.set("quality_check_result", result)

    # ── PR ─────────────────────────────────────────────────────────

    @property
    def pr(self) -> dict[str, Any]:
        return self.load().get("pr", {})

    @property
    def pr_status(self) -> str:
        return self.pr.get("status", "pending")

    @property
    def pr_number(self) -> int | None:
        return self.pr.get("number")

    def set_pr_status(self, status: Literal["pending", "created", "merged"]) -> None:
        def _set(d: dict) -> None:
            d.setdefault("pr", {})["status"] = status
        self.update(_set)

    def set_pr_number(self, number: int) -> None:
        def _set(d: dict) -> None:
            d.setdefault("pr", {})["number"] = number
        self.update(_set)

    # ── CI ─────────────────────────────────────────────────────────

    @property
    def ci(self) -> dict[str, Any]:
        return self.load().get("ci", {})

    @property
    def ci_status(self) -> str:
        return self.ci.get("status", "pending")

    @property
    def ci_results(self) -> list[dict] | None:
        return self.ci.get("results")

    def set_ci_status(self, status: Literal["pending", "passed", "failed"]) -> None:
        def _set(d: dict) -> None:
            d.setdefault("ci", {})["status"] = status
        self.update(_set)

    def set_ci_results(self, results: list[dict]) -> None:
        def _set(d: dict) -> None:
            d.setdefault("ci", {})["results"] = results
        self.update(_set)

    # ── Report ─────────────────────────────────────────────────────

    @property
    def report_written(self) -> bool:
        return self.load().get("report_written", False)

    def set_report_written(self, written: bool = True) -> None:
        self.set("report_written", written)

    # ── Tasks ──────────────────────────────────────────────────────

    @property
    def tasks(self) -> list[str]:
        return self.load().get("tasks", [])

    def add_task(self, task: str) -> None:
        def _add(d: dict) -> None:
            tasks = d.get("tasks", [])
            if task not in tasks:
                tasks.append(task)
            d["tasks"] = tasks

        self.update(_add)

    def set_tasks(self, tasks: list[str]) -> None:
        self.set("tasks", tasks)

    # ── Dependencies ──────────────────────────────────────────────

    @property
    def dependencies(self) -> dict[str, Any]:
        return self.load().get("dependencies", {"packages": [], "installed": False})

    def set_dependencies_packages(self, packages: list[str]) -> None:
        def _set(d: dict) -> None:
            d.setdefault("dependencies", {})["packages"] = packages

        self.update(_set)

    def set_dependencies_installed(self) -> None:
        def _set(d: dict) -> None:
            d.setdefault("dependencies", {})["installed"] = True

        self.update(_set)

    # ── Contracts ─────────────────────────────────────────────────

    @property
    def contracts(self) -> dict[str, Any]:
        return self.load().get("contracts", {
            "file_path": None, "names": [], "code_files": [],
            "written": False, "validated": False,
        })

    @property
    def contract_names(self) -> list[str]:
        return self.contracts.get("names", [])

    def set_contracts_file_path(self, path: str) -> None:
        def _set(d: dict) -> None:
            d.setdefault("contracts", {})["file_path"] = path

        self.update(_set)

    def set_contracts_names(self, names: list[str]) -> None:
        def _set(d: dict) -> None:
            d.setdefault("contracts", {})["names"] = names

        self.update(_set)

    def set_contracts_written(self, written: bool = True) -> None:
        def _set(d: dict) -> None:
            d.setdefault("contracts", {})["written"] = written

        self.update(_set)

    def set_contracts_validated(self, validated: bool = True) -> None:
        def _set(d: dict) -> None:
            d.setdefault("contracts", {})["validated"] = validated

        self.update(_set)

    def add_contract_code_file(self, file_path: str) -> None:
        def _add(d: dict) -> None:
            contracts = d.setdefault("contracts", {})
            code_files = contracts.setdefault("code_files", [])
            if file_path not in code_files:
                code_files.append(file_path)

        self.update(_add)
