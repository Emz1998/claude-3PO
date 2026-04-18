"""state_store.py — Session-scoped JSONL state with file-locking.

Each line in the underlying JSONL file is a complete state snapshot for one
session, identified by ``session_id``. Operations always filter by that ID so
concurrent workflows on the same machine don't collide. A ``filelock``-backed
mutex on a sibling ``.lock`` file serializes read-modify-write cycles across
processes.

The class is deliberately property-heavy: each workflow concept (phases,
plan, tests, code reviews, PR, CI, contracts, project tasks, docs) gets its
own getter/setter accessors so callers never reach into the raw dict. The
trade-off is verbosity in this file; the win is that the JSON schema lives in
exactly one named place per concept.
"""

import json
import time
from pathlib import Path
from typing import Any, Callable, Literal

from models.state import Agent, ReviewResult, State
from filelock import FileLock


class StateStore:
    """Session-scoped JSONL state store with cross-process locking.

    Each session occupies one JSON object on its own line in the file; reads
    and writes always filter by ``session_id`` so multiple sessions can share
    a single state file without collision. Most callers want the high-level
    properties (``current_phase``, ``plan``, ``code_files`` …) rather than
    the raw ``load`` / ``save`` API.

    Example:
        >>> store = StateStore(Path("/tmp/state.jsonl"), "abc")  # doctest: +SKIP
    """

    def __init__(
        self,
        state_path: Path,
        session_id: str,
        default_state: dict[str, Any] | None = None,
    ):
        """
        Bind a store to a path and session.

        Args:
            state_path (Path): JSONL file backing the store. Created on first write.
            session_id (str): Unique session identifier; every operation is
                scoped to this ID.
            default_state (dict[str, Any] | None): Initial dict returned when
                the session has no entry yet. Defaults to ``{}``.

        Example:
            >>> StateStore(Path("/tmp/state.jsonl"), "abc")  # doctest: +SKIP
        """
        self._path = state_path
        self._session_id = session_id
        self._default_state = default_state or {}
        self._lock = FileLock(self._path.with_suffix(".lock"))

    @property
    def session_id(self) -> str:
        """The session ID this store is scoped to.

        Example:
            >>> store.session_id  # doctest: +SKIP
            'abc'
        """
        return self._session_id

    # ── Core I/O ───────────────────────────────────────────────────

    def _read_all_lines(self) -> list[dict[str, Any]]:
        """
        Read every session entry from the JSONL file.

        Malformed lines are silently skipped so one corrupt entry can't
        poison reads for every other session sharing the file. Missing or
        empty file returns ``[]``.

        Example:
            >>> store._read_all_lines()  # doctest: +SKIP
            []
        """
        if not self._path.exists():
            return []
        content = self._path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        entries = []
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def _write_all_lines(self, entries: list[dict[str, Any]]) -> None:
        """Write *entries* back as JSONL, creating parent dirs as needed.

        Example:
            >>> store._write_all_lines([{"session_id": "abc"}])  # doctest: +SKIP
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(e, separators=(",", ":")) for e in entries]
        self._path.write_text(
            "\n".join(lines) + "\n" if lines else "", encoding="utf-8"
        )

    def _find_session(self, entries: list[dict[str, Any]]) -> int:
        """Return the index of the entry matching this session, or ``-1``.

        Example:
            >>> store._find_session([{"session_id": "abc"}])  # doctest: +SKIP
            0
        """
        for i, entry in enumerate(entries):
            if entry.get("session_id") == self._session_id:
                return i
        return -1

    def load(self) -> dict[str, Any]:
        """
        Load this session's snapshot, returning ``default_state`` if absent.

        Returns:
            dict[str, Any]: The session dict (a copy of ``default_state`` if
            this session has never been persisted).

        Example:
            >>> store.load()  # doctest: +SKIP
            {'session_id': 'abc', ...}
        """
        with self._lock:
            entries = self._read_all_lines()
            idx = self._find_session(entries)
            if idx == -1:
                return dict(self._default_state)
            return entries[idx]

    def save(self, state: dict[str, Any] | None = None) -> None:
        """
        Persist *state* (or ``{}``) as this session's snapshot.

        ``session_id`` is always re-stamped onto the saved dict so callers
        can't accidentally orphan a session by writing without it.

        Args:
            state (dict[str, Any] | None): New snapshot. ``None`` writes ``{}``.

        Returns:
            None: Side-effects only.

        Example:
            >>> store.save({"plan": {"written": True}})  # doctest: +SKIP
        """
        with self._lock:
            entries = self._read_all_lines()
            idx = self._find_session(entries)
            data = state if state is not None else {}
            data["session_id"] = self._session_id
            if idx == -1:
                entries.append(data)
            else:
                entries[idx] = data
            self._write_all_lines(entries)

    def update(self, fn: Callable[[dict[str, Any]], None]) -> None:
        """
        Atomically read-mutate-write this session's snapshot under the lock.

        *fn* receives the current dict (or a fresh ``default_state`` if the
        session is brand new) and is expected to mutate it in place. Holding
        the lock across read + mutate + write is what makes concurrent updates
        safe — callers should not call ``load`` then ``save`` separately for
        mutations.

        Args:
            fn (Callable[[dict[str, Any]], None]): Mutator invoked with the
                session dict. Return value is ignored.

        Returns:
            None: Side-effects only.

        Example:
            >>> store.update(lambda d: d.update({"k": 1}))  # doctest: +SKIP
        """
        with self._lock:
            entries = self._read_all_lines()
            idx = self._find_session(entries)
            if idx == -1:
                data = dict(self._default_state)
                data["session_id"] = self._session_id
                fn(data)
                entries.append(data)
            else:
                fn(entries[idx])
            self._write_all_lines(entries)

    # ── Pydantic boundary ─────────────────────────────────────────

    def load_model(self) -> State:
        """
        Load and validate the snapshot as a Pydantic ``State`` model.

        Returns:
            State: Validated state model.

        Raises:
            pydantic.ValidationError: If the on-disk snapshot doesn't satisfy
                the ``State`` schema. Callers that need forgiving dict reads
                should use :meth:`load` instead.

        Example:
            >>> store.load_model()  # doctest: +SKIP
        """
        return State.model_validate(self.load())

    def save_model(self, model: State) -> None:
        """
        Persist a ``State`` model.

        Uses ``model_dump(exclude_unset=False)`` so every field — including
        defaults — is written explicitly. That keeps the JSON shape stable
        across reads even if a field's default changes in code later.

        Args:
            model (State): Pydantic state model to save.

        Example:
            >>> store.save_model(model)  # doctest: +SKIP
        """
        self.save(model.model_dump(exclude_unset=False))

    def get(self, key: str, default: Any = None) -> Any:
        """Look up a single key in the snapshot. Convenience wrapper around ``load().get(...)``.

        Example:
            >>> store.get("workflow_type", "build")  # doctest: +SKIP
            'build'
        """
        data = self.load()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a single top-level key on the snapshot.

        Example:
            >>> store.set("workflow_type", "build")  # doctest: +SKIP
        """
        self.update(lambda d: d.update({key: value}))

    def reinitialize(self, initial_state: dict[str, Any]) -> None:
        """Replace the snapshot entirely with *initial_state* (session_id re-stamped).

        Example:
            >>> store.reinitialize({"workflow_type": "build"})  # doctest: +SKIP
        """
        initial_state["session_id"] = self._session_id
        self.save(initial_state)

    def delete(self) -> None:
        """
        Remove this session's entry from the JSONL file.

        Other sessions in the same file are untouched. No-op if the session
        isn't present.

        Example:
            >>> store.delete()  # doctest: +SKIP
        """
        with self._lock:
            entries = self._read_all_lines()
            entries = [e for e in entries if e.get("session_id") != self._session_id]
            self._write_all_lines(entries)

    @staticmethod
    def _is_active_for_story(entry: dict, story_id: str) -> bool:
        """True if *entry* is an active workflow for *story_id*.

        Example:
            >>> StateStore._is_active_for_story({"story_id": "US-1", "workflow_active": True}, "US-1")
            True
        """
        return (
            entry.get("story_id") == story_id and entry.get("workflow_active") is True
        )

    def find_active_by_story(self, story_id: str) -> list[dict[str, Any]]:
        """
        Return every active session-entry whose ``story_id`` matches.

        Args:
            story_id (str): Story ID to filter by.

        Returns:
            list[dict[str, Any]]: All entries with matching ``story_id`` and
            ``workflow_active is True``.

        Example:
            >>> store.find_active_by_story("US-1")  # doctest: +SKIP
            []
        """
        with self._lock:
            entries = self._read_all_lines()
            return [e for e in entries if self._is_active_for_story(e, story_id)]

    def deactivate_by_story(self, story_id: str) -> int:
        """
        Mark every active session for *story_id* as inactive.

        Used when starting a new workflow on a story whose prior workflows
        haven't been cleanly closed — flips the flag without deleting so the
        old session history stays available for debugging.

        Args:
            story_id (str): Story ID to deactivate.

        Returns:
            int: Number of sessions toggled to inactive.

        Example:
            >>> store.deactivate_by_story("US-1")  # doctest: +SKIP
            0
        """
        with self._lock:
            entries = self._read_all_lines()
            count = 0
            for entry in entries:
                if self._is_active_for_story(entry, story_id):
                    entry["workflow_active"] = False
                    count += 1
            self._write_all_lines(entries)
            return count

    def cleanup_inactive(self, max_age_hours: int = 24) -> int:
        """
        Remove session entries whose ``_last_updated`` is older than *max_age_hours*.

        Entries without a timestamp are kept (conservative — the field may be
        missing on hand-edited sessions). Run periodically to keep the JSONL
        file from growing unbounded.

        Args:
            max_age_hours (int): Cutoff age in hours; defaults to 24.

        Returns:
            int: Number of entries removed.

        Example:
            >>> store.cleanup_inactive(max_age_hours=24)  # doctest: +SKIP
            0
        """
        with self._lock:
            entries = self._read_all_lines()
            cutoff = time.time() - (max_age_hours * 3600)

            kept = []
            removed = 0
            for entry in entries:
                ts = entry.get("_last_updated", 0)
                if ts and ts < cutoff:
                    removed += 1
                else:
                    kept.append(entry)

            self._write_all_lines(kept)
            return removed

    # ── Phases ─────────────────────────────────────────────────────

    @property
    def phases(self) -> list[dict]:
        """All phase entries in the order they were added.

        Example:
            >>> store.phases  # doctest: +SKIP
            [{'name': 'plan', 'status': 'completed'}]
        """
        return self.load().get("phases", [])

    @property
    def current_phase(self) -> str:
        """Name of the most recently added phase, or ``""`` if none yet.

        Example:
            >>> store.current_phase  # doctest: +SKIP
            'plan'
        """
        phases = self.phases
        return phases[-1]["name"] if phases else ""

    def add_phase(self, name: str) -> None:
        """Append a new phase entry with status ``in_progress``.

        Example:
            >>> store.add_phase("plan")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            phases = d.get("phases", [])
            phases.append({"name": name, "status": "in_progress"})
            d["phases"] = phases

        self.update(_add)

    def set_phase_completed(self, name: str) -> None:
        """Mark the first phase entry whose ``name`` matches as ``completed``.

        Example:
            >>> store.set_phase_completed("plan")  # doctest: +SKIP
        """
        def _complete(d: dict) -> None:
            phases = d.get("phases", [])
            for p in phases:
                if p["name"] == name:
                    p["status"] = "completed"
                    break

        self.update(_complete)

    def is_phase_completed(self, name: str) -> bool:
        """True if any phase named *name* is in ``completed`` status.

        Example:
            >>> store.is_phase_completed("plan")  # doctest: +SKIP
            True
        """
        return any(
            p["name"] == name and p["status"] == "completed" for p in self.phases
        )

    def get_phase_status(self, name: str) -> str | None:
        """Return the status of the first phase named *name*, or ``None``.

        Example:
            >>> store.get_phase_status("plan")  # doctest: +SKIP
            'completed'
        """
        for p in self.phases:
            if p["name"] == name:
                return p["status"]
        return None

    # ── Plan revision tracking ──────────────────────────────────────

    @property
    def plan_revised(self) -> bool | None:
        """Tri-state plan revision flag: ``True``, ``False``, or ``None`` (untracked).

        Example:
            >>> store.plan_revised  # doctest: +SKIP
            True
        """
        return self.load().get("plan", {}).get("revised", None)

    def set_plan_revised(self, revised: bool | None) -> None:
        """Set the plan revision flag (use ``None`` to clear it).

        Example:
            >>> store.set_plan_revised(True)  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["revised"] = revised

        self.update(_set)

    # ── Code revision tracking ────────────────────────────────────

    @property
    def files_to_revise(self) -> list[str]:
        """Code files flagged for revision by the latest review.

        Example:
            >>> store.files_to_revise  # doctest: +SKIP
            ['src/foo.py']
        """
        return self.load().get("code_files", {}).get("files_to_revise", [])

    def set_files_to_revise(self, files: list[str]) -> None:
        """Set the to-revise list and reset ``files_revised`` to empty.

        Example:
            >>> store.set_files_to_revise(["src/foo.py"])  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            cf["files_to_revise"] = files
            cf["files_revised"] = []

        self.update(_set)

    @property
    def files_revised(self) -> list[str]:
        """Code files that have been revised since the latest review.

        Example:
            >>> store.files_revised  # doctest: +SKIP
            ['src/foo.py']
        """
        return self.load().get("code_files", {}).get("files_revised", [])

    def add_file_revised(self, file_path: str) -> None:
        """Record *file_path* as revised (deduplicated).

        Example:
            >>> store.add_file_revised("src/foo.py")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            revised = cf.setdefault("files_revised", [])
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    # ── Code review: test revision tracking (TDD) ─────────────────

    @property
    def code_tests_to_revise(self) -> list[str]:
        """Test files flagged for revision during the code-review TDD loop.

        Example:
            >>> store.code_tests_to_revise  # doctest: +SKIP
            ['tests/test_foo.py']
        """
        return self.load().get("code_files", {}).get("tests_to_revise", [])

    def set_code_tests_to_revise(self, files: list[str]) -> None:
        """Set the TDD test-revision list and reset the revised-tests list.

        Example:
            >>> store.set_code_tests_to_revise(["tests/test_foo.py"])  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            cf["tests_to_revise"] = files
            cf["tests_revised"] = []

        self.update(_set)

    @property
    def code_tests_revised(self) -> list[str]:
        """Test files revised during the TDD loop.

        Example:
            >>> store.code_tests_revised  # doctest: +SKIP
            ['tests/test_foo.py']
        """
        return self.load().get("code_files", {}).get("tests_revised", [])

    def add_code_test_revised(self, file_path: str) -> None:
        """Record *file_path* as a revised TDD test (deduplicated).

        Example:
            >>> store.add_code_test_revised("tests/test_foo.py")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            revised = cf.setdefault("tests_revised", [])
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    # ── Agents ─────────────────────────────────────────────────────

    @property
    def agents(self) -> list[dict]:
        """All agent invocations recorded for this session.

        Example:
            >>> store.agents  # doctest: +SKIP
            [{'name': 'Planner', 'status': 'completed'}]
        """
        return self.load().get("agents", [])

    def add_agent(self, agent: Agent) -> None:
        """Append a new agent invocation entry.

        Example:
            >>> store.add_agent(agent)  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            agents = d.get("agents", [])
            agents.append(agent.model_dump())
            d["agents"] = agents

        self.update(_add)

    def get_agent(self, name: str) -> dict[str, Any] | None:
        """Return the first agent entry with the given name, or ``None``.

        Example:
            >>> store.get_agent("Planner")  # doctest: +SKIP
            {'name': 'Planner', 'status': 'completed'}
        """
        agents = self.agents
        return next((a for a in agents if a.get("name") == name), None)

    def count_agents(self, name: str) -> int:
        """Count non-failed agent invocations with the given name.

        Example:
            >>> store.count_agents("QASpecialist")  # doctest: +SKIP
            1
        """
        return sum(
            1
            for a in self.agents
            if a.get("name") == name and a.get("status") != "failed"
        )

    def update_agent_status(
        self, agent_id: str, status: Literal["in_progress", "completed", "failed"]
    ) -> None:
        """Update the status of the agent whose ``tool_use_id`` matches *agent_id*.

        Example:
            >>> store.update_agent_status("toolu_01", "completed")  # doctest: +SKIP
        """
        def _update(d: dict) -> None:
            agents = d.get("agents", [])
            agent = next(
                (a for a in agents if a.get("tool_use_id") == agent_id),
                None,
            )
            if agent:
                agent["status"] = status

        self.update(_update)

    def mark_last_agent_failed(self, name: str) -> None:
        """
        Mark the most recently added agent of *name* as failed.

        Walking from the end means the failure flag attaches to the latest
        invocation specifically — so retry logic that uses ``count_agents``
        (which excludes failed entries) lets the same name be invoked again.

        Args:
            name (str): Agent name to mark.

        Example:
            >>> store.mark_last_agent_failed("Planner")  # doctest: +SKIP
        """
        def _mark(d: dict) -> None:
            agents = d.get("agents", [])
            for a in reversed(agents):
                if a.get("name") == name:
                    a["status"] = "failed"
                    return

        self.update(_mark)

    def agent_rejection_count(self, agent_id: str) -> int:
        """How many times the report from this agent invocation has been rejected.

        Example:
            >>> store.agent_rejection_count("toolu_01")  # doctest: +SKIP
            0
        """
        counts = self.load().get("agent_rejections", {})
        return int(counts.get(agent_id, 0))

    def bump_agent_rejection_count(self, agent_id: str) -> int:
        """
        Increment and return the rejection count for *agent_id*.

        Args:
            agent_id (str): Tool-use ID of the agent invocation.

        Returns:
            int: New count after the increment.

        Example:
            >>> store.bump_agent_rejection_count("toolu_01")  # doctest: +SKIP
            1
        """
        result: dict[str, int] = {"value": 0}

        def _bump(d: dict) -> None:
            counts = d.setdefault("agent_rejections", {})
            counts[agent_id] = int(counts.get(agent_id, 0)) + 1
            result["value"] = counts[agent_id]

        self.update(_bump)
        return result["value"]

    # ── Plan ───────────────────────────────────────────────────────

    @property
    def plan(self) -> dict[str, Any]:
        """The plan sub-dict (file_path, written, reviews, …).

        Example:
            >>> store.plan  # doctest: +SKIP
            {'written': True}
        """
        return self.load().get("plan", {})

    def set_plan_file_path(self, file_path: str) -> None:
        """Record where the plan file was written.

        Example:
            >>> store.set_plan_file_path("/tmp/plan.md")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["file_path"] = file_path

        self.update(_set)

    def set_plan_written(self, written: bool = True) -> None:
        """Toggle the ``plan.written`` flag.

        Example:
            >>> store.set_plan_written(True)  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["written"] = written

        self.update(_set)

    def add_plan_review(
        self,
        scores: dict[Literal["confidence_score", "quality_score"], int],
    ) -> None:
        """Append a plan review record with *scores* and a pending status.

        Example:
            >>> store.add_plan_review({"confidence_score": 80, "quality_score": 90})  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            plan = d.setdefault("plan", {})
            reviews = plan.setdefault("reviews", [])
            reviews.append({"scores": scores, "status": None})

        self.update(_add)

    def set_last_plan_review_status(self, status: ReviewResult) -> None:
        """Set the status of the most recent plan review (no-op if none exist).

        Example:
            >>> store.set_last_plan_review_status("Pass")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            reviews = d.get("plan", {}).get("reviews", [])
            if reviews:
                reviews[-1]["status"] = status

        self.update(_set)

    @property
    def plan_reviews(self) -> list[dict]:
        """All plan review records in order.

        Example:
            >>> store.plan_reviews  # doctest: +SKIP
            [{'scores': {...}, 'status': 'Pass'}]
        """
        return self.load().get("plan", {}).get("reviews", [])

    @property
    def plan_review_count(self) -> int:
        """Number of plan reviews recorded.

        Example:
            >>> store.plan_review_count  # doctest: +SKIP
            1
        """
        return len(self.plan_reviews)

    @property
    def last_plan_review(self) -> dict | None:
        """Most recent plan review, or ``None``.

        Example:
            >>> store.last_plan_review  # doctest: +SKIP
            {'scores': {...}, 'status': 'Pass'}
        """
        reviews = self.plan_reviews
        return reviews[-1] if reviews else None

    # ── Tests ──────────────────────────────────────────────────────

    @property
    def tests(self) -> dict[str, Any]:
        """The tests sub-dict (file_paths, reviews, executed, …).

        Example:
            >>> store.tests  # doctest: +SKIP
            {'file_paths': ['tests/test_foo.py']}
        """
        return self.load().get("tests", {})

    def add_test_file(self, file_path: str) -> None:
        """Record *file_path* as a test file (deduplicated).

        Example:
            >>> store.add_test_file("tests/test_foo.py")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            paths = tests.setdefault("file_paths", [])
            if file_path not in paths:
                paths.append(file_path)

        self.update(_add)

    def add_test_review(self, verdict: str) -> None:
        """Append a test review with the given verdict (Pass/Fail).

        Example:
            >>> store.add_test_review("Pass")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            reviews = tests.setdefault("reviews", [])
            reviews.append({"verdict": verdict})

        self.update(_add)

    @property
    def test_reviews(self) -> list[dict]:
        """All test reviews in order.

        Example:
            >>> store.test_reviews  # doctest: +SKIP
            [{'verdict': 'Pass'}]
        """
        return self.load().get("tests", {}).get("reviews", [])

    @property
    def test_review_count(self) -> int:
        """Number of test reviews recorded.

        Example:
            >>> store.test_review_count  # doctest: +SKIP
            1
        """
        return len(self.test_reviews)

    @property
    def last_test_review(self) -> dict | None:
        """Most recent test review, or ``None``.

        Example:
            >>> store.last_test_review  # doctest: +SKIP
            {'verdict': 'Pass'}
        """
        reviews = self.test_reviews
        return reviews[-1] if reviews else None

    def set_tests_executed(self, executed: bool = True) -> None:
        """Toggle the ``tests.executed`` flag.

        Example:
            >>> store.set_tests_executed(True)  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("tests", {})["executed"] = executed

        self.update(_set)

    # ── Test revision tracking ────────────────────────────────────

    @property
    def test_files_to_revise(self) -> list[str]:
        """Test files flagged for revision by the latest test review.

        Example:
            >>> store.test_files_to_revise  # doctest: +SKIP
            ['tests/test_foo.py']
        """
        return self.load().get("tests", {}).get("files_to_revise", [])

    def set_test_files_to_revise(self, files: list[str]) -> None:
        """Set the test-revision list and reset the revised-files list.

        Example:
            >>> store.set_test_files_to_revise(["tests/test_foo.py"])  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            tests = d.setdefault("tests", {})
            tests["files_to_revise"] = files
            tests["files_revised"] = []

        self.update(_set)

    @property
    def test_files_revised(self) -> list[str]:
        """Test files revised since the latest review.

        Example:
            >>> store.test_files_revised  # doctest: +SKIP
            ['tests/test_foo.py']
        """
        return self.load().get("tests", {}).get("files_revised", [])

    def add_test_file_revised(self, file_path: str) -> None:
        """Record *file_path* as a revised test (deduplicated).

        Example:
            >>> store.add_test_file_revised("tests/test_foo.py")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            revised = tests.setdefault("files_revised", [])
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    # ── Code files to write ──────────────────────────────────────────

    @property
    def code_files_to_write(self) -> list[str]:
        """Files the plan declared the implementer should write.

        Example:
            >>> store.code_files_to_write  # doctest: +SKIP
            ['src/foo.py']
        """
        return self.load().get("code_files_to_write", [])

    def add_code_file_to_write(self, file_path: str) -> None:
        """Append *file_path* to the to-write list (deduplicated).

        Example:
            >>> store.add_code_file_to_write("src/foo.py")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            paths = d.get("code_files_to_write", [])
            if file_path not in paths:
                paths.append(file_path)
            d["code_files_to_write"] = paths

        self.update(_add)

    # ── Code files ─────────────────────────────────────────────────

    @property
    def code_files(self) -> dict[str, Any]:
        """The code_files sub-dict (file_paths, reviews, files_to_revise, …).

        Example:
            >>> store.code_files  # doctest: +SKIP
            {'file_paths': ['src/foo.py']}
        """
        return self.load().get("code_files", {})

    def add_code_file(self, file_path: str) -> None:
        """Record *file_path* as an implementation file (deduplicated).

        Example:
            >>> store.add_code_file("src/foo.py")  # doctest: +SKIP
        """
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
        """Append a code review record with *scores* and a pending status.

        Example:
            >>> store.add_code_review({"confidence_score": 80, "quality_score": 90})  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            reviews = cf.setdefault("reviews", [])
            reviews.append({"scores": scores, "status": None})

        self.update(_add)

    def set_last_code_review_status(self, status: ReviewResult) -> None:
        """Set the status of the most recent code review (no-op if none exist).

        Example:
            >>> store.set_last_code_review_status("Pass")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            reviews = d.get("code_files", {}).get("reviews", [])
            if reviews:
                reviews[-1]["status"] = status

        self.update(_set)

    @property
    def code_reviews(self) -> list[dict]:
        """All code reviews in order.

        Example:
            >>> store.code_reviews  # doctest: +SKIP
            [{'scores': {...}, 'status': 'Pass'}]
        """
        return self.load().get("code_files", {}).get("reviews", [])

    @property
    def code_review_count(self) -> int:
        """Number of code reviews recorded.

        Example:
            >>> store.code_review_count  # doctest: +SKIP
            1
        """
        return len(self.code_reviews)

    @property
    def last_code_review(self) -> dict | None:
        """Most recent code review, or ``None``.

        Example:
            >>> store.last_code_review  # doctest: +SKIP
            {'scores': {...}, 'status': 'Pass'}
        """
        reviews = self.code_reviews
        return reviews[-1] if reviews else None

    # ── Quality check ──────────────────────────────────────────────

    @property
    def quality_check_result(self) -> str | None:
        """Final QA verdict (Pass/Fail), or ``None`` if not yet run.

        Example:
            >>> store.quality_check_result  # doctest: +SKIP
            'Pass'
        """
        return self.load().get("quality_check_result")

    def set_quality_check_result(self, result: ReviewResult) -> None:
        """Record the QA specialist's final verdict.

        Example:
            >>> store.set_quality_check_result("Pass")  # doctest: +SKIP
        """
        self.set("quality_check_result", result)

    @property
    def qa_specialist_count(self) -> int:
        """Number of non-failed QASpecialist invocations.

        Example:
            >>> store.qa_specialist_count  # doctest: +SKIP
            1
        """
        return self.count_agents("QASpecialist")

    # ── PR ─────────────────────────────────────────────────────────

    @property
    def pr(self) -> dict[str, Any]:
        """The pr sub-dict (status, number, …).

        Example:
            >>> store.pr  # doctest: +SKIP
            {'status': 'created', 'number': 42}
        """
        return self.load().get("pr", {})

    @property
    def pr_status(self) -> str:
        """PR status; defaults to ``"pending"`` if unset.

        Example:
            >>> store.pr_status  # doctest: +SKIP
            'created'
        """
        return self.pr.get("status", "pending")

    @property
    def pr_number(self) -> int | None:
        """PR number once created, otherwise ``None``.

        Example:
            >>> store.pr_number  # doctest: +SKIP
            42
        """
        return self.pr.get("number")

    def set_pr_status(self, status: Literal["pending", "created", "merged"]) -> None:
        """Set ``pr.status``.

        Example:
            >>> store.set_pr_status("created")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("pr", {})["status"] = status

        self.update(_set)

    def set_pr_number(self, number: int) -> None:
        """Set ``pr.number``.

        Example:
            >>> store.set_pr_number(42)  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("pr", {})["number"] = number

        self.update(_set)

    # ── CI ─────────────────────────────────────────────────────────

    @property
    def ci(self) -> dict[str, Any]:
        """The ci sub-dict (status, results, …).

        Example:
            >>> store.ci  # doctest: +SKIP
            {'status': 'passed'}
        """
        return self.load().get("ci", {})

    @property
    def ci_status(self) -> str:
        """CI status; defaults to ``"pending"`` if unset.

        Example:
            >>> store.ci_status  # doctest: +SKIP
            'passed'
        """
        return self.ci.get("status", "pending")

    @property
    def ci_results(self) -> list[dict] | None:
        """Per-check CI results, or ``None`` if not yet recorded.

        Example:
            >>> store.ci_results  # doctest: +SKIP
            [{'name': 'test', 'status': 'pass'}]
        """
        return self.ci.get("results")

    def set_ci_status(self, status: Literal["pending", "passed", "failed"]) -> None:
        """Set ``ci.status``.

        Example:
            >>> store.set_ci_status("passed")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("ci", {})["status"] = status

        self.update(_set)

    def set_ci_results(self, results: list[dict]) -> None:
        """Set ``ci.results``.

        Example:
            >>> store.set_ci_results([{"name": "test", "status": "pass"}])  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            d.setdefault("ci", {})["results"] = results

        self.update(_set)

    # ── Report ─────────────────────────────────────────────────────

    @property
    def report_written(self) -> bool:
        """True once the final workflow report has been written.

        Example:
            >>> store.report_written  # doctest: +SKIP
            True
        """
        return self.load().get("report_written", False)

    def set_report_written(self, written: bool = True) -> None:
        """Toggle the report-written flag.

        Example:
            >>> store.set_report_written(True)  # doctest: +SKIP
        """
        self.set("report_written", written)

    # ── Tasks ──────────────────────────────────────────────────────

    @property
    def tasks(self) -> list[str]:
        """Plan-derived task subjects.

        Example:
            >>> store.tasks  # doctest: +SKIP
            ['Write tests', 'Implement']
        """
        return self.load().get("tasks", [])

    def set_tasks(self, tasks: list[str]) -> None:
        """Replace the task list.

        Example:
            >>> store.set_tasks(["Write tests", "Implement"])  # doctest: +SKIP
        """
        self.set("tasks", tasks)

    # ── Created tasks (build workflow — tracks TaskCreate completions) ─

    @property
    def created_tasks(self) -> list[str]:
        """Task subjects already created via TaskCreate during build.

        Example:
            >>> store.created_tasks  # doctest: +SKIP
            ['Write tests']
        """
        return self.load().get("created_tasks", [])

    def add_created_task(self, subject: str) -> None:
        """Record *subject* as a created task (deduplicated).

        Example:
            >>> store.add_created_task("Write tests")  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            ct = d.get("created_tasks", [])
            if subject not in ct:
                ct.append(subject)
            d["created_tasks"] = ct

        self.update(_add)

    # ── Clarify phase fields (build workflow) ─────────────────────

    def get_clarify_phase(self) -> dict | None:
        """Return the clarify phase dict from ``state.phases``, or ``None``.

        Returns:
            dict | None: The phase entry whose ``name`` is ``"clarify"``.

        Example:
            >>> store.get_clarify_phase()  # doctest: +SKIP
            {'name': 'clarify', 'status': 'in_progress', ...}
        """
        for p in self.phases:
            if p.get("name") == "clarify":
                return p
        return None

    def set_clarify_session(self, headless_session_id: str) -> None:
        """Stamp the headless session id and zero the iteration counter.

        Args:
            headless_session_id (str): Session id returned by the initial
                headless ``claude -p`` clarity check.

        Example:
            >>> store.set_clarify_session("sess_abc123")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            for p in d.get("phases", []):
                if p.get("name") == "clarify":
                    p["headless_session_id"] = headless_session_id
                    p["iteration_count"] = 0
                    break

        self.update(_set)

    def bump_clarify_iteration(self) -> None:
        """Increment ``iteration_count`` on the clarify phase by one.

        No-op if the clarify phase is missing — the caller is expected to
        verify it exists before incrementing.

        Example:
            >>> store.bump_clarify_iteration()  # doctest: +SKIP
        """
        def _bump(d: dict) -> None:
            for p in d.get("phases", []):
                if p.get("name") == "clarify":
                    p["iteration_count"] = int(p.get("iteration_count", 0)) + 1
                    break

        self.update(_bump)

    # ── Project tasks (implement workflow) ─────────────────────────

    @property
    def project_tasks(self) -> list[dict]:
        """Top-level project tasks for the implement workflow.

        Example:
            >>> store.project_tasks  # doctest: +SKIP
            [{'id': 'T1', 'subtasks': []}]
        """
        return self.load().get("project_tasks", [])

    def set_project_tasks(self, tasks: list[dict]) -> None:
        """Replace the project-task list wholesale.

        Example:
            >>> store.set_project_tasks([{"id": "T1"}])  # doctest: +SKIP
        """
        self.set("project_tasks", tasks)

    def add_subtask(self, parent_task_id: str, subtask: dict | str) -> None:
        """
        Append a subtask under the project task whose ``id`` matches.

        Dedup logic depends on type: dict subtasks dedupe on ``task_id``,
        string subtasks on the literal value. Mixed types in one parent are
        legal but discouraged.

        Args:
            parent_task_id (str): ID of the project task to attach to.
            subtask (dict | str): Subtask record or label.

        Example:
            >>> store.add_subtask("T1", {"task_id": "T1.1"})  # doctest: +SKIP
        """
        def _add(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    subs = pt.setdefault("subtasks", [])
                    # Dedup by task_id if dict, by value if string
                    if isinstance(subtask, dict):
                        if not any(
                            s.get("task_id") == subtask.get("task_id")
                            for s in subs
                            if isinstance(s, dict)
                        ):
                            subs.append(subtask)
                    else:
                        if subtask not in subs:
                            subs.append(subtask)
                    break

        self.update(_add)

    def set_subtask_completed(self, parent_task_id: str, task_id: str) -> None:
        """Mark a specific subtask under a parent task as completed.

        Example:
            >>> store.set_subtask_completed("T1", "T1.1")  # doctest: +SKIP
        """
        def _complete(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    for sub in pt.get("subtasks", []):
                        if isinstance(sub, dict) and sub.get("task_id") == task_id:
                            sub["status"] = "completed"
                            break
                    break

        self.update(_complete)

    def set_project_task_completed(self, parent_task_id: str) -> None:
        """Mark a top-level project task as completed.

        Example:
            >>> store.set_project_task_completed("T1")  # doctest: +SKIP
        """
        def _complete(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    pt["status"] = "completed"
                    break

        self.update(_complete)

    def get_parent_for_subtask(self, task_id: str) -> str | None:
        """Find the parent project-task ID that owns *task_id*, or ``None``.

        Example:
            >>> store.get_parent_for_subtask("T1.1")  # doctest: +SKIP
            'T1'
        """
        for pt in self.project_tasks:
            for sub in pt.get("subtasks", []):
                if isinstance(sub, dict) and sub.get("task_id") == task_id:
                    return pt.get("id")
        return None

    # ── Plan files to modify (implement workflow) ──────────────────

    @property
    def plan_files_to_modify(self) -> list[str]:
        """Files the plan declared the implement workflow should modify.

        Example:
            >>> store.plan_files_to_modify  # doctest: +SKIP
            ['src/foo.py']
        """
        return self.load().get("plan_files_to_modify", [])

    def set_plan_files_to_modify(self, files: list[str]) -> None:
        """Replace the plan-files-to-modify list.

        Example:
            >>> store.set_plan_files_to_modify(["src/foo.py"])  # doctest: +SKIP
        """
        self.set("plan_files_to_modify", files)

    # ── Docs (specs workflow) ─────────────────────────────────────

    @property
    def docs(self) -> dict[str, Any]:
        """The docs sub-dict — tracks per-doc-key state for the specs workflow.

        Example:
            >>> store.docs  # doctest: +SKIP
            {'architecture': {'written': True}}
        """
        return self.load().get("docs", {})

    def set_doc_written(self, doc_key: str, written: bool) -> None:
        """Toggle the ``written`` flag for *doc_key*.

        Example:
            >>> store.set_doc_written("architecture", True)  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["written"] = written

        self.update(_set)

    def set_doc_path(self, doc_key: str, path: str) -> None:
        """Record the canonical path for *doc_key*.

        Example:
            >>> store.set_doc_path("architecture", "/tmp/arch.md")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["path"] = path

        self.update(_set)

    def set_doc_md_path(self, doc_key: str, path: str) -> None:
        """Record the markdown path for *doc_key* (used when md and JSON are split).

        Example:
            >>> store.set_doc_md_path("architecture", "/tmp/arch.md")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["md_path"] = path

        self.update(_set)

    def set_doc_json_path(self, doc_key: str, path: str) -> None:
        """Record the JSON path for *doc_key* (used when md and JSON are split).

        Example:
            >>> store.set_doc_json_path("architecture", "/tmp/arch.json")  # doctest: +SKIP
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["json_path"] = path

        self.update(_set)

    def is_doc_written(self, doc_key: str) -> bool:
        """True if the ``written`` flag for *doc_key* has been set.

        Example:
            >>> store.is_doc_written("architecture")  # doctest: +SKIP
            True
        """
        return self.docs.get(doc_key, {}).get("written", False)
