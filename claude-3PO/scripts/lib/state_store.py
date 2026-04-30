import json
from pathlib import Path
from typing import Any, Callable, Literal


from filelock import FileLock

Status = Literal["not_started", "in_progress", "completed", "skipped"]
DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"
Verdict = Literal["pass", "fail"]
ReviewType = Literal["plan", "tests", "code", "security", "requirements"]


class StateStore:

    def __init__(
        self,
        state_path: Path = DEFAULT_STATE_PATH,
        default_state: dict[str, Any] | None = None,
    ):

        # Store inputs on self so every method can reach them without reloading.
        self._path = state_path
        # `or {}` keeps the attribute as a real dict even when caller passed None.
        self._default_state = default_state or {}
        # Sibling `.lock` file serializes cross-process writes.
        self._lock = FileLock(self._path.with_suffix(".lock"))

    # ── Core I/O ───────────────────────────────────────────────────

    def _read(self) -> dict[str, Any] | None:

        # Missing file is a valid empty state — no error.
        if not self._path.exists():
            return None
        content = self._path.read_text(encoding="utf-8").strip()
        # Empty file is also a valid empty state.
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Corrupt file → treat as absent; a rewrite will overwrite it.
            return None

    def _write(self, data: dict[str, Any]) -> None:

        # Ensure the target directory exists before writing.
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Compact JSON — single line, no pretty-print indent.
        self._path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    def load(self) -> dict[str, Any]:

        # Lock ensures a stable snapshot across a concurrent writer.
        with self._lock:
            data = self._read()
            # Nothing persisted → hand back a copy of the default.
            if data is None:
                return dict(self._default_state)
            return data

    def save(self, state: dict[str, Any] | None = None) -> None:

        # Exclusive lock for the full read-modify-write.
        with self._lock:
            data = state if state is not None else {}
            self._write(data)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:

        with self._lock:
            data = self._read()
            # Nothing persisted yet → seed from default before the mutator runs.
            if data is None:
                data = dict(self._default_state)
            before = json.dumps(data)
            fn(data)
            after = json.dumps(data)
            if before == after and self._path.exists():
                return
            self._write(data)

    def init(self) -> None:
        data = self._default_state
        self.save(data)

    @property
    def state(self) -> dict[str, Any]:
        return self.load()

    @property
    def session_id(self) -> str:
        return self.state.get("session_id", "")

    @property
    def workflow_status(self) -> str:
        return self.state.get("status", "")

    @property
    def workflow_type(self) -> str:
        return self.state.get("workflow_type", "")

    @property
    def test_mode(self) -> str:
        return self.state.get("test_mode", "")

    @property
    def story_id(self) -> str:
        return self.state.get("story_id", "")

    def set(self, key: str, value: Any) -> None:
        def _set(d: dict[str, Any]) -> None:
            d[key] = value

        self.update(_set)

    def set_session_id(self, session_id: str) -> None:
        self.set("session_id", session_id)

    def set_workflow_active(self, workflow_active: bool) -> None:
        self.set("workflow_active", workflow_active)

    def set_workflow_type(self, workflow_type: str) -> None:
        self.set("workflow_type", workflow_type)

    def set_workflow_status(self, workflow_status: str) -> None:
        self.set("workflow_status", workflow_status)

    def set_story_id(self, story_id: str) -> None:
        self.set("story_id", story_id)

    def set_test_mode(self, test_mode: str) -> None:
        self.set("test_mode", test_mode)

    #  ────────────────── TDD ────────────────────────
    @property
    def tdd(self) -> bool:
        return self.state.get("tdd", False)

    def set_tdd(self, tdd: bool) -> None:
        self.set("tdd", tdd)

    #  ────────────────── File Paths ────────────────────────

    @property
    def file_paths(self) -> list[dict[str, Any]]:
        return self.state.get("paths", [])

    def add_file_path(self, path: str, type: Literal["plan", "test", "code"]) -> None:
        def _add(d: dict[str, Any]) -> None:
            d["paths"].append({"path": path, "type": type})

        self.update(_add)

    def get_file_path(self, type: Literal["plan", "test", "code"]) -> list[str]:
        file_paths = [fp["path"] for fp in self.file_paths if fp["type"] == type]
        return file_paths

    #  ────────────────── Reviews ────────────────────────
    @property
    def reviews(
        self,
    ) -> dict[
        ReviewType,
        list[dict[str, Any]],
    ]:
        return self.state.get("reviews", {})

    def get_reviews(self, review_type: ReviewType) -> list[dict[str, Any]]:
        return self.reviews.get(review_type, [])

    def add_review(
        self,
        confidence_score: int,
        quality_score: int,
        status: Status,
        verdict: Verdict,
    ) -> None:
        def _add(d: dict[str, Any]) -> None:
            d["reviews"].append(
                {
                    "status": status,
                    "confidence_score": confidence_score,
                    "quality_score": quality_score,
                    "verdict": verdict,
                }
            )

        self.update(_add)

    def update_review(
        self,
        review_type: Literal["plan", "tests", "code", "security", "requirements"],
        status: Status,
        verdict: Verdict,
    ) -> None:
        def _update(d: dict[str, Any]) -> None:
            d["reviews"][review_type][-1]["status"] = status
            d["reviews"][review_type][-1]["verdict"] = verdict

        self.update(_update)

    def all_reviews_passed(self, review_type: ReviewType) -> bool:
        return all(
            review["verdict"] == "pass" for review in self.get_reviews(review_type)
        )

    #  ────────────────── Validation Status ────────────────────────
    @property
    def validation_status(self) -> str:
        return self.state.get("validation_status", "")

    def set_validation_status(self, validation_status: str) -> None:
        self.set("validation_status", validation_status)

    #  ────────────────── Skills ────────────────────────

    @property
    def skills(self) -> list[dict[str, Any]]:
        return self.state.get("skills", [])

    def add_skill(self, name: str, status: Status) -> None:
        def _add(d: dict[str, Any]) -> None:
            d["skills"].append({"name": name, "status": status})

        self.update(_add)

    def active_skills(self) -> list[dict[str, Any]]:
        return [s for s in self.skills if s["status"] == "in_progress"]

    def active_skill_names(self) -> list[str]:
        return [s["name"] for s in self.active_skills()]

    def completed_skills(self) -> list[dict[str, Any]]:
        return [s for s in self.skills if s["status"] == "completed"]

    def get_skill_by_status(self, status: Status) -> dict[str, Any] | None:
        return next((s for s in self.skills if s["status"] == status), None)

    def update_skill_status(self, name: str, status: Status) -> None:
        def _update(d: dict[str, Any]) -> None:
            d["skills"][name]["status"] = status

        self.update(_update)

    #  ────────────────── Phases ────────────────────────

    @property
    def phases(self) -> list[dict[str, Any]]:
        return self.state.get("phases", [])

    def add_phase(self, name: str, status: Status) -> None:
        def _add(d: dict[str, Any]) -> None:
            d["phases"].append({"name": name, "status": status})

        self.update(_add)

    @property
    def active_phases(self) -> list[dict[str, Any]]:
        return [s for s in self.phases if s["status"] == "in_progress"]

    @property
    def current_phases(self) -> list[dict[str, Any]]:
        active_phases = self.active_phases
        if not active_phases:
            return [active_phases[-1]]
        return active_phases

    @property
    def current_phases_names(self) -> list[str]:
        return [s["name"] for s in self.current_phases]

    @property
    def completed_phases(self) -> list[dict[str, Any]]:
        return [s for s in self.phases if s["status"] == "completed"]

    @property
    def completed_phases_names(self) -> list[str]:
        return [s["name"] for s in self.completed_phases]

    def get_phase_by_status(self, status: Status) -> dict[str, Any] | None:
        return next((s for s in self.phases if s["status"] == status), None)

    def update_phase_status(self, name: str, status: Status) -> None:
        def _update(d: dict[str, Any]) -> None:
            d["phases"][name]["status"] = status

        self.update(_update)

    def any_active_phase(self) -> bool:
        return any(phase["status"] == "in_progress" for phase in self.phases)

    def all_phases_completed(self) -> bool:
        return all(phase["status"] == "completed" for phase in self.phases)

    #  ────────────────── Agents ────────────────────────
    @property
    def agents(self) -> list[dict[str, Any]]:
        return self.state.get("agents", [])

    def add_agent(self, name: str, status: Status) -> None:
        def _add(d: dict[str, Any]) -> None:
            d["agents"].append({"name": name, "status": status})

        self.update(_add)

    def get_agents_by_status(self, status: Status) -> list[dict[str, Any]]:
        return [a for a in self.agents if a["status"] == status]

    def is_agent_in_progress(self, name: str) -> bool:
        return any(
            agent["name"] == name
            for agent in self.get_agents_by_status(status="in_progress")
        )

    def is_agent_completed(self, agent_name: str) -> bool:
        return all(
            agent["name"] == agent_name
            for agent in self.get_agents_by_status(status="completed")
        )

    def get_agent_status(self, name: str) -> Status:
        return next((a for a in self.agents if a["name"] == name))["status"]

    def get_agents_count(self, name: str, status: Status | None = None) -> int:
        if status is None:
            return len([agent for agent in self.agents if agent["name"] == name])
        return len(
            [
                agent
                for agent in self.agents
                if agent["name"] == name and agent["status"] == status
            ]
        )

    #  ────────────────── Tests ────────────────────────
    @property
    def test_status(self) -> Verdict:
        return self.state.get("tests_status", "")

    def update_test_status(self, status: Verdict) -> None:
        def _update(d: dict[str, Any]) -> None:
            d["tests_status"] = status

        self.update(_update)

    #  ────────────────── Tasks ────────────────────────
    @property
    def tasks_created(self) -> bool:
        return self.state.get("tasks_created", False)

    def set_tasks_created(self, tasks_created: bool) -> None:
        self.set("tasks_created", tasks_created)

    #  ────────────────── Test Review ────────────────────────
    @property
    def tests_status(self) -> Verdict:
        return self.state.get("tests_status", "")

    def update_tests_status(self, status: Verdict) -> None:
        def _update(d: dict[str, Any]) -> None:
            d["tests_status"] = status

        self.update(_update)
