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

from models.state import (
    Agent, CodeReview, DONE_STATUSES, ReviewResult, State, Task,
    TestReview, Validation,
)
from filelock import FileLock


class StateStore:
    """
    Session-scoped JSONL state store with cross-process locking.

    Each session occupies one JSON object on its own line in the file; reads
    and writes always filter by ``session_id`` so multiple sessions can share
    a single state file without collision. Most callers want the high-level
    properties (``current_phase``, ``plan``, ``code_files`` …) rather than
    the raw ``load`` / ``save`` API.

    Example:
        >>> store = StateStore(Path("/tmp/state.jsonl"), "abc")  # doctest: +SKIP
        Return: <StateStore>
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

        Returns:
            None: Constructor — stores the inputs on ``self``.

        Example:
            >>> StateStore(Path("/tmp/state.jsonl"), "abc")  # doctest: +SKIP
            Return: <StateStore>
        """
        # Store inputs on self so every method can reach them without reloading.
        self._path = state_path
        self._session_id = session_id
        # `or {}` keeps the attribute as a real dict even when caller passed None.
        self._default_state = default_state or {}
        # Sibling `.lock` file serializes cross-process writes.
        self._lock = FileLock(self._path.with_suffix(".lock"))

    @property
    def session_id(self) -> str:
        """
        The session ID this store is scoped to.

        Returns:
            str: The immutable session identifier passed to ``__init__``.

        Example:
            >>> store.session_id  # doctest: +SKIP
            Return: 'abc'
        """
        # Expose the private attribute read-only — no setter.
        return self._session_id

    # ── Core I/O ───────────────────────────────────────────────────

    def _read_all_lines(self) -> list[dict[str, Any]]:
        """
        Read every session entry from the JSONL file.

        Malformed lines are silently skipped so one corrupt entry can't
        poison reads for every other session sharing the file. Missing or
        empty file returns ``[]``.

        Returns:
            list[dict[str, Any]]: All parseable session entries in file order.

        Example:
            >>> store._read_all_lines()  # doctest: +SKIP
            Return: []
        """
        # Missing file is a valid empty state — no error.
        if not self._path.exists():
            return []
        content = self._path.read_text(encoding="utf-8").strip()
        # Empty file is also a valid empty state.
        if not content:
            return []
        entries = []
        # One JSON object per line; skip malformed lines to stay resilient.
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    # Preserve other sessions even when one entry is corrupt.
                    continue
        return entries

    def _write_all_lines(self, entries: list[dict[str, Any]]) -> None:
        """
        Write *entries* back as JSONL, creating parent dirs as needed.

        Args:
            entries (list[dict[str, Any]]): Full set of session entries to persist.

        Returns:
            None: Side-effects only.

        SideEffect:
            Writes all session entries to the JSONL file on disk.

        Example:
            >>> store._write_all_lines([{"session_id": "abc"}])  # doctest: +SKIP
            Return: None
            SideEffect:
                state.jsonl file written with all sessions
        """
        # Ensure the target directory exists before writing.
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Compact JSON (no whitespace) keeps each session on one line.
        lines = [json.dumps(e, separators=(",", ":")) for e in entries]
        # Trailing newline when any entries; empty string when none.
        self._path.write_text(
            "\n".join(lines) + "\n" if lines else "", encoding="utf-8"
        )

    def _find_session(self, entries: list[dict[str, Any]]) -> int:
        """
        Return the index of the entry matching this session, or ``-1``.

        Args:
            entries (list[dict[str, Any]]): Session entries to scan.

        Returns:
            int: Index of the matching entry, or ``-1`` if not found.

        Example:
            >>> store._find_session([{"session_id": "abc"}])  # doctest: +SKIP
            Return: 0
        """
        # Linear scan — session counts are small (tens, not thousands).
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
            Return: {'session_id': 'abc'}
        """
        # Lock ensures a stable snapshot across a concurrent writer.
        with self._lock:
            entries = self._read_all_lines()
            idx = self._find_session(entries)
            # Session not yet persisted → hand back a copy of the default.
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

        SideEffect:
            Replaces this session's entire snapshot in the JSONL file.

        Example:
            >>> store.save({"plan": {"written": True}})  # doctest: +SKIP
            Return: None
            SideEffect:
                state replaced and persisted
        """
        # Exclusive lock for the full read-modify-write.
        with self._lock:
            entries = self._read_all_lines()
            idx = self._find_session(entries)
            data = state if state is not None else {}
            # Re-stamp id so callers can never orphan the entry.
            data["session_id"] = self._session_id
            if idx == -1:
                # First write for this session — append.
                entries.append(data)
            else:
                # Existing entry — overwrite in place.
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

        SideEffect:
            Reads, mutates, and writes the session snapshot under lock.

        Example:
            >>> store.update(lambda d: d.update({"k": 1}))  # doctest: +SKIP
            Return: None
            SideEffect:
                state mutated and persisted
        """
        with self._lock:
            entries = self._read_all_lines()
            idx = self._find_session(entries)
            if idx == -1:
                # Brand-new session: seed from default, stamp id, mutate, append.
                data = dict(self._default_state)
                data["session_id"] = self._session_id
                fn(data)
                entries.append(data)
            else:
                # Mutate in place on the existing entry.
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
            Return: State(session_id='abc', ...)
        """
        # Fresh dict → Pydantic validates and coerces defaults on load.
        return State.model_validate(self.load())

    def save_model(self, model: State) -> None:
        """
        Persist a ``State`` model.

        Uses ``model_dump(exclude_unset=False)`` so every field — including
        defaults — is written explicitly. That keeps the JSON shape stable
        across reads even if a field's default changes in code later.

        Args:
            model (State): Pydantic state model to save.

        Returns:
            None: Side-effects only.

        SideEffect:
            Persists the full Pydantic State model to the JSONL file.

        Example:
            >>> store.save_model(model)  # doctest: +SKIP
            Return: None
            SideEffect:
                state model persisted
        """
        # exclude_unset=False → defaults land on disk, stabilizing the schema.
        self.save(model.model_dump(exclude_unset=False))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Look up a single key in the snapshot.

        Convenience wrapper around ``load().get(key, default)`` so callers
        don't need to materialize the whole dict for a one-key read.

        Args:
            key (str): Top-level snapshot key.
            default (Any): Value returned when *key* is absent.

        Returns:
            Any: Value for *key* or *default*.

        Example:
            >>> store.get("workflow_type", "build")  # doctest: +SKIP
            Return: 'build'
        """
        # Single load — caller handles downstream gets themselves.
        data = self.load()
        return data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a single top-level key on the snapshot.

        Args:
            key (str): Top-level snapshot key.
            value (Any): New value (arbitrary JSON-serializable object).

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[key] and persists to JSONL.

        Example:
            >>> store.set("workflow_type", "build")  # doctest: +SKIP
            Return: None
            SideEffect:
                state["workflow_type"] = "build"
        """
        # Single-key update — callers with multiple writes should use set_many.
        self.update(lambda d: d.update({key: value}))

    def set_many(self, fields: dict[str, Any]) -> None:
        """
        Merge *fields* onto the snapshot in one locked read-modify-write.

        Batches multiple top-level writes into a single lock acquisition to
        avoid the per-call file-rewrite overhead of looping over ``set``.

        Args:
            fields (dict[str, Any]): Key/value pairs to merge into the snapshot.

        Returns:
            None: Side-effects only — snapshot mutated in place on disk.

        SideEffect:
            Sets multiple top-level keys and persists in one locked write.

        Example:
            >>> store.set_many({"status": "completed", "workflow_active": False})  # doctest: +SKIP
            Return: None
            SideEffect:
                state[status] = "completed"
                state[workflow_active] = False
        """
        # Empty dict → skip the lock acquisition entirely; nothing to merge.
        if not fields:
            return
        # Single update() call keeps the write atomic across all keys.
        self.update(lambda d: d.update(fields))

    def reinitialize(self, initial_state: dict[str, Any]) -> None:
        """
        Replace the snapshot entirely with *initial_state*.

        Session id is re-stamped so callers can pass a raw dict without
        remembering to include it themselves.

        Args:
            initial_state (dict[str, Any]): New snapshot body.

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces this session's entire snapshot in the JSONL file.

        Example:
            >>> store.reinitialize({"workflow_type": "build"})  # doctest: +SKIP
            Return: None
            SideEffect:
                state = {"workflow_type": "build"}
        """
        # Stamp session id before save so the entry is routable.
        initial_state["session_id"] = self._session_id
        self.save(initial_state)

    def delete(self) -> None:
        """
        Remove this session's entry from the JSONL file.

        Other sessions in the same file are untouched. No-op if the session
        isn't present.

        Returns:
            None: Side-effects only.

        SideEffect:
            Removes this session's entry from the JSONL file.

        Example:
            >>> store.delete()  # doctest: +SKIP
            Return: None
            SideEffect:
                session removed from JSONL
        """
        with self._lock:
            entries = self._read_all_lines()
            # Filter out this session; everyone else survives untouched.
            entries = [e for e in entries if e.get("session_id") != self._session_id]
            self._write_all_lines(entries)

    @staticmethod
    def _is_active_for_story(entry: dict, story_id: str) -> bool:
        """
        Check whether *entry* is an active workflow for *story_id*.

        Args:
            entry (dict): Raw session entry loaded from the JSONL file.
            story_id (str): Story ID to match against.

        Returns:
            bool: ``True`` when both the story id matches and the
            ``workflow_active`` flag is set; ``False`` otherwise.

        Example:
            >>> StateStore._is_active_for_story({"story_id": "US-1", "workflow_active": True}, "US-1")
            Return: True
        """
        # Both conditions must hold — inactive sessions belong to history.
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
            Return: []
        """
        with self._lock:
            entries = self._read_all_lines()
            # Filter delegates to the shared active-session predicate.
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

        SideEffect:
            Flips ``workflow_active`` to ``False`` for matching entries in the JSONL file.

        Example:
            >>> store.deactivate_by_story("US-1")  # doctest: +SKIP
            Return: 0
            SideEffect:
                state[workflow_active] = False (matching sessions)
        """
        with self._lock:
            entries = self._read_all_lines()
            count = 0
            # Flip flag in place; don't delete so history survives.
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

        SideEffect:
            Removes stale entries from the JSONL file.

        Example:
            >>> store.cleanup_inactive(max_age_hours=24)  # doctest: +SKIP
            Return: 0
            SideEffect:
                stale entries removed from JSONL
        """
        with self._lock:
            entries = self._read_all_lines()
            # Cutoff = current wall time minus the retention window.
            cutoff = time.time() - (max_age_hours * 3600)

            kept = []
            removed = 0
            for entry in entries:
                ts = entry.get("_last_updated", 0)
                # Only drop entries with a real timestamp older than cutoff.
                if ts and ts < cutoff:
                    removed += 1
                else:
                    kept.append(entry)

            self._write_all_lines(kept)
            return removed

    # ── Phases ─────────────────────────────────────────────────────

    @property
    def phases(self) -> list[dict]:
        """
        All phase entries in the order they were added.

        Returns:
            list[dict]: Phase records shaped ``{"name": str, "status": str}``.

        Example:
            >>> store.phases  # doctest: +SKIP
            Return: [{'name': 'plan', 'status': 'completed'}]
        """
        # Single load — callers that iterate repeatedly should snapshot the result.
        return self.load().get("phases", [])

    @property
    def current_phase(self) -> str:
        """
        Name of the most recently added phase, or ``""`` if none yet.

        Returns:
            str: Latest phase name, or empty string when no phases exist.

        Example:
            >>> store.current_phase  # doctest: +SKIP
            Return: 'plan'
        """
        # Snapshot the list once — avoids a second file read via self.phases.
        phases = self.phases
        return phases[-1]["name"] if phases else ""

    def add_phase(
        self,
        name: str,
        status: Literal["in_progress", "completed", "skipped"] = "in_progress",
    ) -> None:
        """
        Append a new phase entry with the given *status*.

        The ``status`` parameter lets callers record a phase that was
        skipped or already-completed without a second ``set_phase_completed``
        round-trip.

        Args:
            name (str): Phase name (e.g. ``"plan"``, ``"code"``).
            status (Literal["in_progress", "completed", "skipped"]): Initial
                phase status. Defaults to ``"in_progress"``.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[phases].

        Example:
            >>> store.add_phase("plan")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases] = [..., {"name": "plan", "status": "in_progress"}] # Default: in_progress
            >>> store.add_phase("skip-me", status="skipped")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases] = [..., {"name": "skip-me", "status": "skipped"}]

        """
        def _add(d: dict) -> None:
            # Read-or-default the existing phase list before appending.
            phases = d.get("phases", [])
            phases.append({"name": name, "status": status})
            d["phases"] = phases

        self.update(_add)

    def set_phase_completed(self, name: str) -> None:
        """
        Mark the first phase entry whose ``name`` matches as ``completed``.

        Args:
            name (str): Phase name to complete.

        Returns:
            None: Side-effects only — no-op when phase is missing.

        SideEffect:
            Updates state[phases][i][status].

        Example:
            >>> store.set_phase_completed("plan")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases][i][status] = "completed"
        """
        def _complete(d: dict) -> None:
            phases = d.get("phases", [])
            # First match wins — duplicate phase names are not expected.
            for p in phases:
                if p["name"] == name:
                    p["status"] = "completed"
                    break

        self.update(_complete)

    def is_phase_completed(self, name: str) -> bool:
        """
        Check whether any phase named *name* reached ``completed`` status.

        Args:
            name (str): Phase name.

        Returns:
            bool: ``True`` when at least one matching phase is completed.

        Example:
            >>> store.is_phase_completed("plan")  # doctest: +SKIP
            Return: True
        """
        # Stricter than is_phase_done — ignores "skipped".
        return any(
            p["name"] == name and p["status"] == "completed" for p in self.phases
        )

    def get_phase_status(self, name: str) -> str | None:
        """
        Look up the status of the first phase named *name*.

        Args:
            name (str): Phase name.

        Returns:
            str | None: Phase status string, or ``None`` when missing.

        Example:
            >>> store.get_phase_status("plan")  # doctest: +SKIP
            Return: 'completed'
        """
        # First match wins; phase names are unique per session by convention.
        for p in self.phases:
            if p["name"] == name:
                return p["status"]
        return None

    def is_phase_done(self, name: str) -> bool:
        """
        Check whether *name*'s phase has reached a terminal status.

        ``DONE_STATUSES`` treats both ``completed`` and ``skipped`` as done —
        workflow routing should not gate on one over the other.

        Args:
            name (str): Phase name to look up.

        Returns:
            bool: ``True`` if the phase status is in ``DONE_STATUSES``,
            else ``False`` (also ``False`` when the phase is missing).

        Example:
            >>> store.is_phase_done("plan")  # doctest: +SKIP
            Return: True
        """
        # Delegate status lookup; None falls through as "not done".
        return self.get_phase_status(name) in DONE_STATUSES

    def done_phase_names(self) -> list[str]:
        """
        List names of every phase in a terminal status.

        Order matches phase insertion order so callers can reconstruct the
        workflow timeline.

        Returns:
            list[str]: Names of completed or skipped phases, oldest first.

        Example:
            >>> store.done_phase_names()  # doctest: +SKIP
            Return: ['explore', 'plan']
        """
        # Snapshot phases once — self.phases triggers a full file read.
        return [p["name"] for p in self.phases if p["status"] in DONE_STATUSES]

    # ── Plan revision tracking ──────────────────────────────────────

    @property
    def plan_revised(self) -> bool | None:
        """
        Tri-state plan revision flag: ``True``, ``False``, or ``None``.

        ``None`` distinguishes "not yet tracked" from an explicit ``False``,
        which is useful when the workflow hasn't decided whether revision is
        required.

        Returns:
            bool | None: Revision flag, or ``None`` when never set.

        Example:
            >>> store.plan_revised  # doctest: +SKIP
            Return: True if set else None
        """
        # Defensive .get chain — plan sub-dict may not exist yet.
        return self.load().get("plan", {}).get("revised", None)

    def set_plan_revised(self, revised: bool | None) -> None:
        """
        Set the plan revision flag.

        Args:
            revised (bool | None): ``True``/``False`` to flip the flag,
                ``None`` to reset to "untracked".

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[plan][revised].

        Example:
            >>> store.set_plan_revised(True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan][revised] = True
        """
        def _set(d: dict) -> None:
            # Ensure plan sub-dict exists before writing the flag.
            d.setdefault("plan", {})["revised"] = revised

        self.update(_set)

    # ── Code revision tracking ────────────────────────────────────

    @property
    def files_to_revise(self) -> list[str]:
        """
        Code files flagged for revision by the latest review.

        Returns:
            list[str]: File paths the reviewer marked for a follow-up pass.

        Example:
            >>> store.files_to_revise  # doctest: +SKIP
            Return: ['src/foo.py']
        """
        # Defensive .get chain — code_files may not exist yet.
        return self.load().get("code_files", {}).get("files_to_revise", [])

    def set_files_to_revise(self, files: list[str]) -> None:
        """
        Replace the to-revise list and reset ``files_revised`` to empty.

        Resetting ``files_revised`` alongside makes the revision loop
        restart-safe: each new review seeds a fresh to-do/done pair.

        Args:
            files (list[str]): New to-revise file paths.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[code_files][files_to_revise]; resets files_revised.

        Example:
            >>> store.set_files_to_revise(["src/foo.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][files_to_revise] = ["src/foo.py"], state[code_files][files_revised] = []
        """
        def _set(d: dict) -> None:
            # Ensure code_files exists, then overwrite both lists together.
            cf = d.setdefault("code_files", {})
            cf["files_to_revise"] = files
            cf["files_revised"] = []

        self.update(_set)

    @property
    def files_revised(self) -> list[str]:
        """
        Code files that have been revised since the latest review.

        Returns:
            list[str]: File paths recorded as revised.

        Example:
            >>> store.files_revised  # doctest: +SKIP
            Return: ['src/foo.py']
        """
        return self.load().get("code_files", {}).get("files_revised", [])

    def add_file_revised(self, file_path: str) -> None:
        """
        Record *file_path* as revised (deduplicated).

        Args:
            file_path (str): Path of the revised code file.

        Returns:
            None: Side-effects only — duplicates are silently ignored.

        SideEffect:
            Appends to state[code_files][files_revised].

        Example:
            >>> store.add_file_revised("src/foo.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][files_revised] = [..., "src/foo.py"]
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            revised = cf.setdefault("files_revised", [])
            # Dedup keeps the list idempotent under retries.
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    # ── Code review: test revision tracking (TDD) ─────────────────

    @property
    def code_tests_to_revise(self) -> list[str]:
        """
        Test files flagged for revision during the code-review TDD loop.

        Returns:
            list[str]: Paths the reviewer wants the implementer to update.

        Example:
            >>> store.code_tests_to_revise  # doctest: +SKIP
            Return: ['tests/test_foo.py']
        """
        return self.load().get("code_files", {}).get("tests_to_revise", [])

    def set_code_tests_to_revise(self, files: list[str]) -> None:
        """
        Replace the TDD test-revision list and reset the revised-tests list.

        Pairs with :meth:`add_code_test_revised` to model the to-do / done
        transition for test revisions in the TDD loop.

        Args:
            files (list[str]): Tests that need revision.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[code_files][tests_to_revise]; resets tests_revised.

        Example:
            >>> store.set_code_tests_to_revise(["tests/test_foo.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][tests_to_revise] = ["tests/test_foo.py"]
state[code_files][tests_revised] = []
        """
        def _set(d: dict) -> None:
            # Overwrite both lists together so the revision loop restarts cleanly.
            cf = d.setdefault("code_files", {})
            cf["tests_to_revise"] = files
            cf["tests_revised"] = []

        self.update(_set)

    @property
    def code_tests_revised(self) -> list[str]:
        """
        Test files revised during the TDD loop.

        Returns:
            list[str]: Paths recorded as revised since the last to-revise reset.

        Example:
            >>> store.code_tests_revised  # doctest: +SKIP
            Return: ['tests/test_foo.py']
        """
        return self.load().get("code_files", {}).get("tests_revised", [])

    def add_code_test_revised(self, file_path: str) -> None:
        """
        Record *file_path* as a revised TDD test (deduplicated).

        Args:
            file_path (str): Path of the revised test file.

        Returns:
            None: Side-effects only — duplicates ignored.

        SideEffect:
            Appends to state[code_files][tests_revised].

        Example:
            >>> store.add_code_test_revised("tests/test_foo.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][tests_revised] = [..., "tests/test_foo.py"]
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            revised = cf.setdefault("tests_revised", [])
            # Dedup — retried dispatches must not double-count.
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    # ── Agents ─────────────────────────────────────────────────────

    @property
    def agents(self) -> list[dict]:
        """
        All agent invocations recorded for this session.

        Returns:
            list[dict]: Agent records ordered by invocation time.

        Example:
            >>> store.agents  # doctest: +SKIP
            Return: [{'name': 'Planner', 'status': 'completed'}]
        """
        return self.load().get("agents", [])

    def add_agent(self, agent: Agent) -> None:
        """
        Append a new agent invocation entry.

        Args:
            agent (Agent): Pydantic agent record; dumped to a plain dict
                before persistence.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[agents].

        Example:
            >>> store.add_agent(agent)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[agents] = [..., agent.model_dump(])
        """
        def _add(d: dict) -> None:
            agents = d.get("agents", [])
            # Dump to dict so the JSONL file stays schema-agnostic.
            agents.append(agent.model_dump())
            d["agents"] = agents

        self.update(_add)

    def get_agent(self, name: str) -> dict[str, Any] | None:
        """
        Look up the first agent entry with the given name.

        Args:
            name (str): Agent name to search for.

        Returns:
            dict[str, Any] | None: First matching entry, or ``None``.

        Example:
            >>> store.get_agent("Planner")  # doctest: +SKIP
            Return: {'name': 'Planner', 'status': 'completed'}
        """
        # Single snapshot — avoids re-reading the file during iteration.
        agents = self.agents
        return next((a for a in agents if a.get("name") == name), None)

    def count_agents(self, name: str) -> int:
        """
        Count non-failed agent invocations with the given name.

        Excluding failures lets retry logic check whether the name is "still
        allowed" without tripping on historical failures.

        Args:
            name (str): Agent name to count.

        Returns:
            int: Number of matching non-failed invocations.

        Example:
            >>> store.count_agents("QASpecialist")  # doctest: +SKIP
            Return: 1
        """
        # Sum 1 per match; `!= "failed"` excludes explicit failure entries.
        return sum(
            1
            for a in self.agents
            if a.get("name") == name and a.get("status") != "failed"
        )

    def update_agent_status(
        self, agent_id: str, status: Literal["in_progress", "completed", "failed"]
    ) -> None:
        """
        Update the status of the agent whose ``tool_use_id`` matches *agent_id*.

        Args:
            agent_id (str): Tool-use ID of the invocation.
            status (Literal["in_progress", "completed", "failed"]): New status.

        Returns:
            None: Side-effects only — no-op when agent_id is unknown.

        SideEffect:
            Updates state[agents][i][status] by tool_use_id.

        Example:
            >>> store.update_agent_status("toolu_01", "completed")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[agents][i][status] = "completed"
        """
        def _update(d: dict) -> None:
            agents = d.get("agents", [])
            # First (and should be only) entry with this tool_use_id.
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

        Returns:
            None: Side-effects only — no-op when no match exists.

        SideEffect:
            Sets state[agents][i][status] = "failed".

        Example:
            >>> store.mark_last_agent_failed("Planner")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[agents][i][status] = "failed"
        """
        def _mark(d: dict) -> None:
            agents = d.get("agents", [])
            # Reverse walk — only the latest matching entry gets the flag.
            for a in reversed(agents):
                if a.get("name") == name:
                    a["status"] = "failed"
                    return

        self.update(_mark)

    def agent_rejection_count(self, agent_id: str) -> int:
        """
        Look up how many times this agent's report has been rejected.

        Args:
            agent_id (str): Tool-use ID of the agent invocation.

        Returns:
            int: Current rejection count (0 when never rejected).

        Example:
            >>> store.agent_rejection_count("toolu_01")  # doctest: +SKIP
            Return: 0
        """
        # Defensive .get chain — rejections map may not exist yet.
        counts = self.load().get("agent_rejections", {})
        return int(counts.get(agent_id, 0))

    def bump_agent_rejection_count(self, agent_id: str) -> int:
        """
        Increment and return the rejection count for *agent_id*.

        Args:
            agent_id (str): Tool-use ID of the agent invocation.

        Returns:
            int: New count after the increment.

        SideEffect:
            Persists the incremented rejection count to the JSONL state file.

        Example:
            >>> store.bump_agent_rejection_count("toolu_01")  # doctest: +SKIP
            Return: 1
            SideEffect:
                state[agent_rejections][agent_id] = (previous + 1)
        """
        # Box the post-update value so the caller can read it after the closure.
        result: dict[str, int] = {"value": 0}

        def _bump(d: dict) -> None:
            counts = d.setdefault("agent_rejections", {})
            counts[agent_id] = int(counts.get(agent_id, 0)) + 1
            # Snapshot the new value for the outer return.
            result["value"] = counts[agent_id]

        self.update(_bump)
        return result["value"]

    # ── Plan ───────────────────────────────────────────────────────

    @property
    def plan(self) -> dict[str, Any]:
        """
        The plan sub-dict (file_path, written, reviews, …).

        Returns:
            dict[str, Any]: Plan state or ``{}`` when unset.

        Example:
            >>> store.plan  # doctest: +SKIP
            Return: {'written': True}
        """
        return self.load().get("plan", {})

    def set_plan_file_path(self, file_path: str) -> None:
        """
        Record where the plan file was written.

        Args:
            file_path (str): Path on disk to the plan markdown.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[plan][file_path].

        Example:
            >>> store.set_plan_file_path("/tmp/plan.md")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan][file_path] = "/tmp/plan.md"
        """
        def _set(d: dict) -> None:
            # Ensure plan sub-dict exists before stamping the path.
            d.setdefault("plan", {})["file_path"] = file_path

        self.update(_set)

    def set_plan_written(self, written: bool = True) -> None:
        """
        Toggle the ``plan.written`` flag.

        Args:
            written (bool): ``True`` (default) to mark written; ``False`` to clear.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[plan][written].

        Example:
            >>> store.set_plan_written(True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan][written] = True
        """
        def _set(d: dict) -> None:
            d.setdefault("plan", {})["written"] = written

        self.update(_set)

    def add_plan_review(
        self,
        scores: dict[Literal["confidence_score", "quality_score"], int],
    ) -> None:
        """
        Append a plan review record with *scores* and a pending status.

        Status is initialized to ``None`` so the reviewer can set Pass/Fail
        later via :meth:`set_last_plan_review_status`.

        Args:
            scores (dict[Literal["confidence_score", "quality_score"], int]):
                Reviewer's score pair.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[plan][reviews].

        Example:
            >>> store.add_plan_review({"confidence_score": 80, "quality_score": 90})  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan][reviews] = [..., {"scores": {...}, "status": None}]
        """
        def _add(d: dict) -> None:
            # plan and reviews both created-on-demand.
            plan = d.setdefault("plan", {})
            reviews = plan.setdefault("reviews", [])
            reviews.append({"scores": scores, "status": None})

        self.update(_add)

    def set_last_plan_review_status(self, status: ReviewResult) -> None:
        """
        Set the status of the most recent plan review.

        Args:
            status (ReviewResult): Pass/Fail verdict to stamp on the latest review.

        Returns:
            None: Side-effects only — no-op when no reviews exist.

        SideEffect:
            Updates state[plan][reviews][-1][status].

        Example:
            >>> store.set_last_plan_review_status("Pass")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan][reviews][-1][status] = "Pass"
        """
        def _set(d: dict) -> None:
            reviews = d.get("plan", {}).get("reviews", [])
            # Only stamp the trailing review; ignore when list is empty.
            if reviews:
                reviews[-1]["status"] = status

        self.update(_set)

    @property
    def plan_reviews(self) -> list[dict]:
        """
        All plan review records in order.

        Returns:
            list[dict]: Review records oldest-first.

        Example:
            >>> store.plan_reviews  # doctest: +SKIP
            Return: [{'scores': {'confidence_score': 80}, 'status': 'Pass'}]
        """
        return self.load().get("plan", {}).get("reviews", [])

    @property
    def plan_review_count(self) -> int:
        """
        Number of plan reviews recorded.

        Returns:
            int: Length of ``plan.reviews``.

        Example:
            >>> store.plan_review_count  # doctest: +SKIP
            Return: 1
        """
        return len(self.plan_reviews)

    @property
    def last_plan_review(self) -> dict | None:
        """
        Most recent plan review, or ``None``.

        Returns:
            dict | None: Trailing review record, or ``None`` when no reviews exist.

        Example:
            >>> store.last_plan_review  # doctest: +SKIP
            Return: {'scores': {'confidence_score': 80}, 'status': 'Pass'}
        """
        # Snapshot once so the list isn't re-read for both the index and None check.
        reviews = self.plan_reviews
        return reviews[-1] if reviews else None

    # ── Tests ──────────────────────────────────────────────────────

    @property
    def tests(self) -> dict[str, Any]:
        """
        The tests sub-dict (file_paths, reviews, executed, …).

        Returns:
            dict[str, Any]: Tests state or ``{}`` when unset.

        Example:
            >>> store.tests  # doctest: +SKIP
            Return: {'file_paths': ['tests/test_foo.py']}
        """
        return self.load().get("tests", {})

    def add_test_file(self, file_path: str) -> None:
        """
        Record *file_path* as a test file (deduplicated).

        Args:
            file_path (str): Path of the test file.

        Returns:
            None: Side-effects only — duplicates silently ignored.

        SideEffect:
            Appends to state[tests][file_paths].

        Example:
            >>> store.add_test_file("tests/test_foo.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][file_paths] = [..., "tests/test_foo.py"]
        """
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            paths = tests.setdefault("file_paths", [])
            # Dedup — same path may be reported by multiple dispatches.
            if file_path not in paths:
                paths.append(file_path)

        self.update(_add)

    def add_test_review(self, verdict: str) -> None:
        """
        Append a test review with the given verdict (Pass/Fail).

        Args:
            verdict (str): Reviewer's verdict string.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[tests][reviews].

        Example:
            >>> store.add_test_review("Pass")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][reviews] = [..., {"verdict": verdict}]
        """
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            reviews = tests.setdefault("reviews", [])
            reviews.append({"verdict": verdict})

        self.update(_add)

    @property
    def test_reviews(self) -> list[dict]:
        """
        All test reviews in order.

        Returns:
            list[dict]: Review records oldest-first.

        Example:
            >>> store.test_reviews  # doctest: +SKIP
            Return: [{'verdict': 'Pass'}]
        """
        return self.load().get("tests", {}).get("reviews", [])

    @property
    def test_review_count(self) -> int:
        """
        Number of test reviews recorded.

        Returns:
            int: Length of ``tests.reviews``.

        Example:
            >>> store.test_review_count  # doctest: +SKIP
            Return: 1
        """
        return len(self.test_reviews)

    @property
    def last_test_review(self) -> dict | None:
        """
        Most recent test review, or ``None``.

        Returns:
            dict | None: Trailing review record, or ``None`` when no reviews exist.

        Example:
            >>> store.last_test_review  # doctest: +SKIP
            Return: {'verdict': 'Pass'}
        """
        # Snapshot once so the list isn't re-read for both the index and None check.
        reviews = self.test_reviews
        return reviews[-1] if reviews else None

    def set_tests_executed(self, executed: bool = True) -> None:
        """
        Toggle the ``tests.executed`` flag.

        Args:
            executed (bool): ``True`` (default) if tests were executed.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[tests][executed].

        Example:
            >>> store.set_tests_executed(True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][executed] =  true
        """
        def _set(d: dict) -> None:
            d.setdefault("tests", {})["executed"] = executed

        self.update(_set)

    # ── Test revision tracking ────────────────────────────────────

    @property
    def test_files_to_revise(self) -> list[str]:
        """
        Test files flagged for revision by the latest test review.

        Returns:
            list[str]: Paths that still need revision.

        Example:
            >>> store.test_files_to_revise  # doctest: +SKIP
            Return: ['tests/test_foo.py']
        """
        return self.load().get("tests", {}).get("files_to_revise", [])

    def set_test_files_to_revise(self, files: list[str]) -> None:
        """
        Replace the test-revision list and reset the revised-files list.

        Resetting ``files_revised`` alongside keeps the revision loop
        restart-safe for a fresh review cycle.

        Args:
            files (list[str]): New to-revise paths.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[tests][files_to_revise]; resets files_revised.

        Example:
            >>> store.set_test_files_to_revise(["tests/test_foo.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][files_to_revise] = ["tests/test_foo.py"]
                state[tests][files_revised] = []
        """
        def _set(d: dict) -> None:
            # Overwrite both lists together — same pattern as set_files_to_revise.
            tests = d.setdefault("tests", {})
            tests["files_to_revise"] = files
            tests["files_revised"] = []

        self.update(_set)

    @property
    def test_files_revised(self) -> list[str]:
        """
        Test files revised since the latest review.

        Returns:
            list[str]: Paths recorded as revised.

        Example:
            >>> store.test_files_revised  # doctest: +SKIP
            Return: ['tests/test_foo.py']
        """
        return self.load().get("tests", {}).get("files_revised", [])

    def add_test_file_revised(self, file_path: str) -> None:
        """
        Record *file_path* as a revised test (deduplicated).

        Args:
            file_path (str): Path of the revised test file.

        Returns:
            None: Side-effects only — duplicates silently ignored.

        SideEffect:
            Appends to state[tests][files_revised].

        Example:
            >>> store.add_test_file_revised("tests/test_foo.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][files_revised] = [..., "tests/test_foo.py"]
        """
        def _add(d: dict) -> None:
            tests = d.setdefault("tests", {})
            revised = tests.setdefault("files_revised", [])
            # Dedup — retried dispatches must not double-count.
            if file_path not in revised:
                revised.append(file_path)

        self.update(_add)

    # ── Code files to write ──────────────────────────────────────────

    @property
    def code_files_to_write(self) -> list[str]:
        """
        Files the plan declared the implementer should write.

        Returns:
            list[str]: Planned file paths.

        Example:
            >>> store.code_files_to_write  # doctest: +SKIP
            Return: ['src/foo.py']
        """
        return self.load().get("code_files_to_write", [])

    def add_code_file_to_write(self, file_path: str) -> None:
        """
        Append *file_path* to the to-write list (deduplicated).

        Args:
            file_path (str): Path the implementer is expected to write.

        Returns:
            None: Side-effects only — duplicates silently ignored.

        SideEffect:
            Appends to state[code_files_to_write].

        Example:
            >>> store.add_code_file_to_write("src/foo.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files_to_write] = [..., "src/foo.py"]
        """
        def _add(d: dict) -> None:
            paths = d.get("code_files_to_write", [])
            # Dedup — plan may reference the same file multiple times.
            if file_path not in paths:
                paths.append(file_path)
            d["code_files_to_write"] = paths

        self.update(_add)

    # ── Code files ─────────────────────────────────────────────────

    @property
    def code_files(self) -> dict[str, Any]:
        """
        The code_files sub-dict (file_paths, reviews, files_to_revise, …).

        Returns:
            dict[str, Any]: Code-files state or ``{}`` when unset.

        Example:
            >>> store.code_files  # doctest: +SKIP
            Return: {'file_paths': ['src/foo.py']}
        """
        return self.load().get("code_files", {})

    def add_code_file(self, file_path: str) -> None:
        """
        Record *file_path* as an implementation file (deduplicated).

        Args:
            file_path (str): Path of the implementation file.

        Returns:
            None: Side-effects only — duplicates silently ignored.

        SideEffect:
            Appends to state[code_files][file_paths].

        Example:
            >>> store.add_code_file("src/foo.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][file_paths] = [..., "src/foo.py"]
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            paths = cf.setdefault("file_paths", [])
            # Dedup — same file may be reported by multiple write dispatches.
            if file_path not in paths:
                paths.append(file_path)

        self.update(_add)

    def add_code_review(
        self,
        scores: dict[Literal["confidence_score", "quality_score"], int],
    ) -> None:
        """
        Append a code review record with *scores* and a pending status.

        Args:
            scores (dict[Literal["confidence_score", "quality_score"], int]):
                Reviewer's score pair.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[code_files][reviews].

        Example:
            >>> store.add_code_review({"confidence_score": 80, "quality_score": 90})  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][reviews] = [..., {"scores": {...}, "status": None}]
        """
        def _add(d: dict) -> None:
            cf = d.setdefault("code_files", {})
            reviews = cf.setdefault("reviews", [])
            # Status starts None; set_last_code_review_status stamps Pass/Fail later.
            reviews.append({"scores": scores, "status": None})

        self.update(_add)

    def set_last_code_review_status(self, status: ReviewResult) -> None:
        """
        Set the status of the most recent code review.

        Args:
            status (ReviewResult): Pass/Fail verdict for the latest review.

        Returns:
            None: Side-effects only — no-op when no reviews exist.

        SideEffect:
            Updates state[code_files][reviews][-1][status].

        Example:
            >>> store.set_last_code_review_status("Pass")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][reviews][-1][status] = "Pass"
        """
        def _set(d: dict) -> None:
            reviews = d.get("code_files", {}).get("reviews", [])
            # Only stamp the trailing review; ignore when list is empty.
            if reviews:
                reviews[-1]["status"] = status

        self.update(_set)

    @property
    def code_reviews(self) -> list[dict]:
        """
        All code reviews in order.

        Returns:
            list[dict]: Review records oldest-first.

        Example:
            >>> store.code_reviews  # doctest: +SKIP
            Return: [{'scores': {'confidence_score': 80}, 'status': 'Pass'}]
        """
        return self.load().get("code_files", {}).get("reviews", [])

    @property
    def code_review_count(self) -> int:
        """
        Number of code reviews recorded.

        Returns:
            int: Length of ``code_files.reviews``.

        Example:
            >>> store.code_review_count  # doctest: +SKIP
            Return: 1
        """
        return len(self.code_reviews)

    @property
    def last_code_review(self) -> dict | None:
        """
        Most recent code review, or ``None``.

        Returns:
            dict | None: Trailing review record, or ``None`` when no reviews exist.

        Example:
            >>> store.last_code_review  # doctest: +SKIP
            Return: {'scores': {'confidence_score': 80}, 'status': 'Pass'}
        """
        # Snapshot once so the list isn't re-read for both the index and None check.
        reviews = self.code_reviews
        return reviews[-1] if reviews else None

    # ── Quality check ──────────────────────────────────────────────

    @property
    def quality_check_result(self) -> str | None:
        """
        Final QA verdict (Pass/Fail), or ``None`` if not yet run.

        Returns:
            str | None: QA verdict string, or ``None`` when unset.

        Example:
            >>> store.quality_check_result  # doctest: +SKIP
            Return: 'Pass'
        """
        return self.load().get("quality_check_result")

    def set_quality_check_result(self, result: ReviewResult) -> None:
        """
        Record the QA specialist's final verdict.

        Args:
            result (ReviewResult): Pass/Fail verdict.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[quality_check_result].

        Example:
            >>> store.set_quality_check_result("Pass")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[quality_check_result] = "Pass"
        """
        # Delegate to the generic top-level setter.
        self.set("quality_check_result", result)

    @property
    def qa_specialist_count(self) -> int:
        """
        Number of non-failed QASpecialist invocations.

        Returns:
            int: Count via :meth:`count_agents`.

        Example:
            >>> store.qa_specialist_count  # doctest: +SKIP
            Return: 1
        """
        # Alias for count_agents to keep the QA caller intent-visible.
        return self.count_agents("QASpecialist")

    # ── PR ─────────────────────────────────────────────────────────

    @property
    def pr(self) -> dict[str, Any]:
        """
        The pr sub-dict (status, number, …).

        Returns:
            dict[str, Any]: PR state or ``{}`` when unset.

        Example:
            >>> store.pr  # doctest: +SKIP
            Return: {'status': 'created', 'number': 42}
        """
        return self.load().get("pr", {})

    @property
    def pr_status(self) -> str:
        """
        PR status; defaults to ``"pending"`` if unset.

        Returns:
            str: Current PR status.

        Example:
            >>> store.pr_status  # doctest: +SKIP
            Return: 'created'
        """
        return self.pr.get("status", "pending")

    @property
    def pr_number(self) -> int | None:
        """
        PR number once created, otherwise ``None``.

        Returns:
            int | None: PR number, or ``None`` when not yet created.

        Example:
            >>> store.pr_number  # doctest: +SKIP
            Return: 42
        """
        return self.pr.get("number")

    def set_pr_status(self, status: Literal["pending", "created", "merged"]) -> None:
        """
        Set ``pr.status``.

        Args:
            status (Literal["pending", "created", "merged"]): New PR status.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[pr][status].

        Example:
            >>> store.set_pr_status("created")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[pr][status] = "created"
        """
        def _set(d: dict) -> None:
            d.setdefault("pr", {})["status"] = status

        self.update(_set)

    def set_pr_number(self, number: int) -> None:
        """
        Set ``pr.number``.

        Args:
            number (int): PR number returned by GitHub.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[pr][number].

        Example:
            >>> store.set_pr_number(42)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[pr][number] = 42
        """
        def _set(d: dict) -> None:
            d.setdefault("pr", {})["number"] = number

        self.update(_set)

    # ── CI ─────────────────────────────────────────────────────────

    @property
    def ci(self) -> dict[str, Any]:
        """
        The ci sub-dict (status, results, …).

        Returns:
            dict[str, Any]: CI state or ``{}`` when unset.

        Example:
            >>> store.ci  # doctest: +SKIP
            Return: {'status': 'passed'}
        """
        return self.load().get("ci", {})

    @property
    def ci_status(self) -> str:
        """
        CI status; defaults to ``"pending"`` if unset.

        Returns:
            str: Current CI status string.

        Example:
            >>> store.ci_status  # doctest: +SKIP
            Return: 'passed'
        """
        return self.ci.get("status", "pending")

    @property
    def ci_results(self) -> list[dict] | None:
        """
        Per-check CI results, or ``None`` if not yet recorded.

        Returns:
            list[dict] | None: CI check results, or ``None`` when unset.

        Example:
            >>> store.ci_results  # doctest: +SKIP
            Return: [{'name': 'test', 'status': 'pass'}]
        """
        return self.ci.get("results")

    def set_ci_status(self, status: Literal["pending", "passed", "failed"]) -> None:
        """
        Set ``ci.status``.

        Args:
            status (Literal["pending", "passed", "failed"]): New CI status.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[ci][status].

        Example:
            >>> store.set_ci_status("passed")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[ci][status] = "passed"
        """
        def _set(d: dict) -> None:
            d.setdefault("ci", {})["status"] = status

        self.update(_set)

    def set_ci_results(self, results: list[dict]) -> None:
        """
        Set ``ci.results``.

        Args:
            results (list[dict]): Per-check results from GitHub.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[ci][results].

        Example:
            >>> store.set_ci_results([{"name": "test", "status": "pass"}])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[ci][results] = [{"name": "test", "status": "pass"}]
        """
        def _set(d: dict) -> None:
            d.setdefault("ci", {})["results"] = results

        self.update(_set)

    # ── Report ─────────────────────────────────────────────────────

    @property
    def report_written(self) -> bool:
        """
        True once the final workflow report has been written.

        Returns:
            bool: ``True`` when report has been persisted; ``False`` otherwise.

        Example:
            >>> store.report_written  # doctest: +SKIP
            Return: True
        """
        return self.load().get("report_written", False)

    def set_report_written(self, written: bool = True) -> None:
        """
        Toggle the report-written flag.

        Args:
            written (bool): ``True`` (default) once the report is persisted.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[report_written].

        Example:
            >>> store.set_report_written(True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[report_written] = written
        """
        self.set("report_written", written)

    # ── Tasks ──────────────────────────────────────────────────────

    @property
    def tasks(self) -> list[str]:
        """
        Plan-derived task subjects.

        Returns:
            list[str]: Ordered subjects extracted from the plan.

        Example:
            >>> store.tasks  # doctest: +SKIP
            Return: ['Write tests', 'Implement']
        """
        return self.load().get("tasks", [])

    def set_tasks(self, tasks: list[str]) -> None:
        """
        Replace the task list.

        Args:
            tasks (list[str]): New ordered subjects.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[tasks].

        Example:
            >>> store.set_tasks(["Write tests", "Implement"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tasks] = ["Write tests", "Implement"]
        """
        self.set("tasks", tasks)

    # ── Created tasks (build workflow — tracks TaskCreate completions) ─

    @property
    def created_tasks(self) -> list[str]:
        """
        Task subjects already created via TaskCreate during build.

        Returns:
            list[str]: Subjects recorded after a successful TaskCreate.

        Example:
            >>> store.created_tasks  # doctest: +SKIP
            Return: ['Write tests']
        """
        return self.load().get("created_tasks", [])

    def add_created_task(self, subject: str) -> None:
        """
        Record *subject* as a created task (deduplicated).

        Args:
            subject (str): Subject of the just-created task.

        Returns:
            None: Side-effects only — duplicates silently ignored.

        SideEffect:
            Appends to state[created_tasks].

        Example:
            >>> store.add_created_task("Write tests")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[created_tasks] = [..., "Write tests"]
        """
        def _add(d: dict) -> None:
            ct = d.get("created_tasks", [])
            # Dedup — TaskCreate hooks may fire twice on retry.
            if subject not in ct:
                ct.append(subject)
            d["created_tasks"] = ct

        self.update(_add)

    # ── Clarify phase fields (build workflow) ─────────────────────

    def get_clarify_phase(self) -> dict | None:
        """
        Look up the clarify phase dict from ``state.phases``.

        Returns:
            dict | None: The phase entry whose ``name`` is ``"clarify"``,
            or ``None`` when no clarify phase was added.

        Example:
            >>> store.get_clarify_phase()  # doctest: +SKIP
            Return: {'name': 'clarify', 'status': 'in_progress'}
        """
        # Linear scan — phase lists are short.
        for p in self.phases:
            if p.get("name") == "clarify":
                return p
        return None

    def set_clarify_session(self, headless_session_id: str) -> None:
        """
        Stamp the headless session id and zero the iteration counter.

        Args:
            headless_session_id (str): Session id returned by the initial
                headless ``claude -p`` clarity check.

        Returns:
            None: Side-effects only — no-op when clarify phase is missing.

        SideEffect:
            Sets state[phases][clarify][headless_session_id]; resets iteration_count.

        Example:
            >>> store.set_clarify_session("sess_abc123")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases][clarify][headless_session_id] = "sess_abc123"
        """
        def _set(d: dict) -> None:
            # Find the clarify phase entry; first match wins.
            for p in d.get("phases", []):
                if p.get("name") == "clarify":
                    p["headless_session_id"] = headless_session_id
                    # Reset iteration_count — caller is starting a fresh loop.
                    p["iteration_count"] = 0
                    break

        self.update(_set)

    def bump_clarify_iteration(self) -> None:
        """
        Increment ``iteration_count`` on the clarify phase by one.

        No-op if the clarify phase is missing — the caller is expected to
        verify it exists before incrementing.

        Returns:
            None: Side-effects only.

        SideEffect:
            Increments state[phases][clarify][iteration_count].

        Example:
            >>> store.bump_clarify_iteration()  # doctest: +SKIP
            Return: None
            SideEffect:
                state[phases][clarify][iteration_count] = (previous + 1)
        """
        def _bump(d: dict) -> None:
            # First clarify phase entry — unique per session by convention.
            for p in d.get("phases", []):
                if p.get("name") == "clarify":
                    p["iteration_count"] = int(p.get("iteration_count", 0)) + 1
                    break

        self.update(_bump)

    # ── Project tasks (implement workflow) ─────────────────────────

    @property
    def project_tasks(self) -> list[dict]:
        """
        Top-level project tasks for the implement workflow.

        Returns:
            list[dict]: Task records, each optionally carrying a ``subtasks`` list.

        Example:
            >>> store.project_tasks  # doctest: +SKIP
            Return: [{'id': 'T1', 'subtasks': []}]
        """
        return self.load().get("project_tasks", [])

    def set_project_tasks(self, tasks: list[dict]) -> None:
        """
        Replace the project-task list wholesale.

        Args:
            tasks (list[dict]): New project-task records.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[project_tasks].

        Example:
            >>> store.set_project_tasks([{"id": "T1"}])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks] = [{"id": "T1"}]
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

        Returns:
            None: Side-effects only — no-op when parent is missing.

        SideEffect:
            Appends to state[project_tasks][i][subtasks].

        Example:
            >>> store.add_subtask("T1", {"task_id": "T1.1"})  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks][i][subtasks].append(subtask)
        """
        def _add(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            # Find the parent; skip if no match.
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    subs = pt.setdefault("subtasks", [])
                    # Dedup key differs by shape: dicts use task_id, strings use value.
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
        """
        Mark a specific subtask under a parent task as completed.

        Args:
            parent_task_id (str): Parent project task ID.
            task_id (str): Subtask task_id to mark completed.

        Returns:
            None: Side-effects only — no-op when either id is missing.

        SideEffect:
            Sets state[project_tasks][i][subtasks][j][status].

        Example:
            >>> store.set_subtask_completed("T1", "T1.1")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks][i][subtasks][j][status] = "completed"
        """
        def _complete(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            # Find the parent task first …
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    # … then the matching subtask inside it.
                    for sub in pt.get("subtasks", []):
                        if isinstance(sub, dict) and sub.get("task_id") == task_id:
                            sub["status"] = "completed"
                            break
                    break

        self.update(_complete)

    def set_project_task_completed(self, parent_task_id: str) -> None:
        """
        Mark a top-level project task as completed.

        Args:
            parent_task_id (str): Project task ID.

        Returns:
            None: Side-effects only — no-op when parent is missing.

        SideEffect:
            Sets state[project_tasks][i][status].

        Example:
            >>> store.set_project_task_completed("T1")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks][i][status] = "completed"
        """
        def _complete(d: dict) -> None:
            ptasks = d.get("project_tasks", [])
            for pt in ptasks:
                if pt.get("id") == parent_task_id:
                    pt["status"] = "completed"
                    break

        self.update(_complete)

    def get_parent_for_subtask(self, task_id: str) -> str | None:
        """
        Find the parent project-task ID that owns *task_id*.

        Args:
            task_id (str): Subtask task_id.

        Returns:
            str | None: Parent project-task ID, or ``None`` when not found.

        Example:
            >>> store.get_parent_for_subtask("T1.1")  # doctest: +SKIP
            Return: 'T1'
        """
        # Two-level scan — project tasks and their subtasks.
        for pt in self.project_tasks:
            for sub in pt.get("subtasks", []):
                if isinstance(sub, dict) and sub.get("task_id") == task_id:
                    return pt.get("id")
        return None

    # ── Plan files to modify (implement workflow) ──────────────────

    @property
    def plan_files_to_modify(self) -> list[str]:
        """
        Files the plan declared the implement workflow should modify.

        Returns:
            list[str]: Planned target files.

        Example:
            >>> store.plan_files_to_modify  # doctest: +SKIP
            Return: ['src/foo.py']
        """
        return self.load().get("plan_files_to_modify", [])

    def set_plan_files_to_modify(self, files: list[str]) -> None:
        """
        Replace the plan-files-to-modify list.

        Args:
            files (list[str]): New target file paths.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[plan_files_to_modify].

        Example:
            >>> store.set_plan_files_to_modify(["src/foo.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan_files_to_modify] = ["src/foo.py"]
        """
        self.set("plan_files_to_modify", files)

    # ── Docs (specs workflow) ─────────────────────────────────────

    @property
    def docs(self) -> dict[str, Any]:
        """
        The docs sub-dict — tracks per-doc-key state for the specs workflow.

        Returns:
            dict[str, Any]: Doc state keyed by doc identifier.

        Example:
            >>> store.docs  # doctest: +SKIP
            Return: {'architecture': {'written': True}}
        """
        return self.load().get("docs", {})

    def set_doc_written(self, doc_key: str, written: bool) -> None:
        """
        Toggle the ``written`` flag for *doc_key*.

        Args:
            doc_key (str): Identifier of the doc entry.
            written (bool): ``True`` once the doc is persisted.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][written].

        Example:
            >>> store.set_doc_written("architecture", True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][written] = True
        """
        def _set(d: dict) -> None:
            # docs and per-key sub-dict created on demand.
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["written"] = written

        self.update(_set)

    def set_doc_path(self, doc_key: str, path: str) -> None:
        """
        Record the canonical path for *doc_key*.

        Args:
            doc_key (str): Identifier of the doc entry.
            path (str): Absolute or workflow-relative path.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][path].

        Example:
            >>> store.set_doc_path("architecture", "/tmp/arch.md")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][path] = "/tmp/arch.md"
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["path"] = path

        self.update(_set)

    def set_doc_md_path(self, doc_key: str, path: str) -> None:
        """
        Record the markdown path for *doc_key*.

        Used when the doc is stored as an ``.md`` / ``.json`` pair — keeps
        the two paths under a single doc entry.

        Args:
            doc_key (str): Identifier of the doc entry.
            path (str): Path to the ``.md`` file.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][md_path].

        Example:
            >>> store.set_doc_md_path("architecture", "/tmp/arch.md")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][md_path] = "/tmp/arch.md"
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["md_path"] = path

        self.update(_set)

    def set_doc_json_path(self, doc_key: str, path: str) -> None:
        """
        Record the JSON path for *doc_key*.

        Used when the doc is stored as an ``.md`` / ``.json`` pair.

        Args:
            doc_key (str): Identifier of the doc entry.
            path (str): Path to the ``.json`` file.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[docs][doc_key][json_path].

        Example:
            >>> store.set_doc_json_path("architecture", "/tmp/arch.json")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[docs]["architecture"][json_path] = "/tmp/arch.json"
        """
        def _set(d: dict) -> None:
            docs = d.setdefault("docs", {})
            docs.setdefault(doc_key, {})["json_path"] = path

        self.update(_set)

    def is_doc_written(self, doc_key: str) -> bool:
        """
        Check whether the ``written`` flag for *doc_key* has been set.

        Args:
            doc_key (str): Identifier of the doc entry.

        Returns:
            bool: ``True`` when the doc is marked written.

        Example:
            >>> store.is_doc_written("architecture")  # doctest: +SKIP
            Return: True
        """
        # Defensive .get chain — docs/doc_key sub-dicts may not exist.
        return self.docs.get(doc_key, {}).get("written", False)

    # ── Flat-API sinks (consume Recorder-built data classes) ──────

    def _replace_in_section(self, section: str, field: str, value: Any) -> None:
        """
        Set ``state[section][field] = value`` under the lock.

        Shared backend for the ``set_<section>_<field>`` sinks so the
        section/field routing lives in one place instead of six lambdas.

        Args:
            section (str): Top-level key (created if missing).
            field (str): Sub-key inside *section*.
            value (Any): Replacement value (the caller handles coercion).

        Returns:
            None: Side-effects only.

        SideEffect:
            Updates state[section][field] in the JSONL file.

        Example:
            >>> store._replace_in_section("tests", "file_paths", ["t.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state["tests"]["file_paths"] = ["t.py"]
        """
        def _set(d: dict) -> None:
            # setdefault guarantees the section dict exists before we assign.
            d.setdefault(section, {})[field] = value

        self.update(_set)

    def _append_unique_in_section(self, section: str, field: str, value: Any) -> None:
        """
        Append *value* to ``state[section][field]`` unless it's already present.

        Dedup keeps the flagged-for-revision lists idempotent when the
        Recorder re-dispatches the same file across retries.

        Args:
            section (str): Top-level key (created if missing).
            field (str): List sub-key inside *section* (created if missing).
            value (Any): Item to append.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[section][field] array (deduplicated).

        Example:
            >>> store._append_unique_in_section("tests", "files_to_revise", "t.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[section][field] = [..., value]
        """
        def _add(d: dict) -> None:
            # Materialize the list in place; later `value not in xs` dedup.
            xs = d.setdefault(section, {}).setdefault(field, [])
            if value not in xs:
                xs.append(value)

        self.update(_add)

    def add_command(self, command: str) -> None:
        """
        Append *command* to ``state.commands``.

        Args:
            command (str): Literal command string (e.g. ``"pytest"``).

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[commands].

        Example:
            >>> store.add_command("pytest")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[commands] = [..., "pytest"]
        """
        def _add(d: dict) -> None:
            # Commands list grows monotonically — no dedup here.
            d.setdefault("commands", []).append(command)

        self.update(_add)

    def add_validation(self, validation: Validation) -> None:
        """
        Append a :class:`Validation` record to ``state.validations``.

        Args:
            validation (Validation): Pydantic validation record; stored as
                its ``model_dump()`` form for JSON round-tripping.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[validations].

        Example:
            >>> store.add_validation(Validation(result="pass"))  # doctest: +SKIP
            Return: None
            SideEffect:
                state[validations] = [..., validation.model_dump(])
        """
        def _add(d: dict) -> None:
            # Dump to plain dict so the JSONL file stays schema-agnostic.
            d.setdefault("validations", []).append(validation.model_dump())

        self.update(_add)

    def add_project_task(self, task: Task) -> None:
        """
        Append a :class:`Task` to ``project_tasks`` (dedup by ``task_id``).

        Dedup makes the Recorder safe to re-dispatch the same TaskCreate
        without producing duplicate project_tasks entries.

        Args:
            task (Task): Pydantic task record.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[project_tasks] (dedup by task_id).

        Example:
            >>> store.add_project_task(Task(task_id="T-1", subject="x"))  # doctest: +SKIP
            Return: None
            SideEffect:
                state[project_tasks] = [..., task.model_dump(])
        """
        def _add(d: dict) -> None:
            tasks = d.setdefault("project_tasks", [])
            # Skip if any existing record already owns this task_id.
            if not any(t.get("task_id") == task.task_id for t in tasks):
                tasks.append(task.model_dump())

        self.update(_add)

    def add_code_review_record(self, review: CodeReview) -> None:
        """
        Append a full :class:`CodeReview` to ``code_files.reviews``.

        Unlike :meth:`add_code_review`, this writes every review field
        (scores, status, files_to_revise, …) in one call rather than the
        two-step scores-then-status pattern.

        Args:
            review (CodeReview): Pydantic review record.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends full review to state[code_files][reviews].

        Example:
            >>> store.add_code_review_record(review)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][reviews] = [..., review.model_dump(])
        """
        def _add(d: dict) -> None:
            # code_files/reviews sub-dicts created on demand.
            reviews = d.setdefault("code_files", {}).setdefault("reviews", [])
            reviews.append(review.model_dump())

        self.update(_add)

    def add_test_review_record(self, review: TestReview) -> None:
        """
        Append a full :class:`TestReview` to ``tests.reviews``.

        Mirror of :meth:`add_code_review_record` for the test review flow.

        Args:
            review (TestReview): Pydantic review record.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends full review to state[tests][reviews].

        Example:
            >>> store.add_test_review_record(review)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][reviews] = [..., review.model_dump(])
        """
        def _add(d: dict) -> None:
            # tests/reviews sub-dicts created on demand.
            reviews = d.setdefault("tests", {}).setdefault("reviews", [])
            reviews.append(review.model_dump())

        self.update(_add)

    def set_test_mode(self, value: bool | str) -> None:
        """
        Set ``state.test_mode``.

        The field is union-typed because earlier workflows wrote a bool and
        newer ones write a mode string (``"e2e"`` / ``"unit"``); both shapes
        are still readable from disk.

        Args:
            value (bool | str): Test mode flag or named mode.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[test_mode].

        Example:
            >>> store.set_test_mode("e2e")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[test_mode] = "e2e"
        """
        # Pass-through to the generic top-level setter.
        self.set("test_mode", value)

    def set_report_file_path(self, file_path: str) -> None:
        """
        Set ``state.report_file_path``.

        Args:
            file_path (str): Absolute or workflow-relative path to the report.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[report_file_path].

        Example:
            >>> store.set_report_file_path("r.md")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[report_file_path] = "r.md"
        """
        self.set("report_file_path", file_path)

    def set_tdd(self, tdd: bool) -> None:
        """
        Set ``state.tdd``.

        Args:
            tdd (bool): ``True`` when the workflow is TDD-gated.

        Returns:
            None: Side-effects only.

        SideEffect:
            Sets state[tdd].

        Example:
            >>> store.set_tdd(True)  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tdd] = True
        """
        self.set("tdd", tdd)

    def set_plan_reviews(self, reviews: list[dict]) -> None:
        """
        Replace ``plan.reviews`` wholesale.

        Args:
            reviews (list[dict]): New reviews list; copied to detach from
                the caller's reference.

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[plan][reviews].

        Example:
            >>> store.set_plan_reviews([])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[plan][reviews] = []
        """
        # list() copy so later caller mutations don't leak into state.
        self._replace_in_section("plan", "reviews", list(reviews))

    def set_test_reviews(self, reviews: list[dict]) -> None:
        """
        Replace ``tests.reviews`` wholesale.

        Args:
            reviews (list[dict]): New reviews list (copied).

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[tests][reviews].

        Example:
            >>> store.set_test_reviews([])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][reviews] = []
        """
        self._replace_in_section("tests", "reviews", list(reviews))

    def set_code_reviews(self, reviews: list[dict]) -> None:
        """
        Replace ``code_files.reviews`` wholesale.

        Args:
            reviews (list[dict]): New reviews list (copied).

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[code_files][reviews].

        Example:
            >>> store.set_code_reviews([])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][reviews] = []
        """
        self._replace_in_section("code_files", "reviews", list(reviews))

    def set_test_file_paths(self, paths: list[str]) -> None:
        """
        Replace ``tests.file_paths``.

        Args:
            paths (list[str]): Full list of test files (copied).

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[tests][file_paths].

        Example:
            >>> store.set_test_file_paths(["t.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][file_paths] = ["t.py"]
        """
        self._replace_in_section("tests", "file_paths", list(paths))

    def set_code_file_paths(self, paths: list[str]) -> None:
        """
        Replace ``code_files.file_paths``.

        Args:
            paths (list[str]): Full list of code files (copied).

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[code_files][file_paths].

        Example:
            >>> store.set_code_file_paths(["a.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][file_paths] = ["a.py"]
        """
        self._replace_in_section("code_files", "file_paths", list(paths))

    def set_test_files_revised(self, paths: list[str]) -> None:
        """
        Replace ``tests.files_revised``.

        Args:
            paths (list[str]): Test files marked revised (copied).

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[tests][files_revised].

        Example:
            >>> store.set_test_files_revised(["t.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][files_revised] = ["t.py"]
        """
        self._replace_in_section("tests", "files_revised", list(paths))

    def set_code_files_revised(self, paths: list[str]) -> None:
        """
        Replace ``code_files.files_revised``.

        Args:
            paths (list[str]): Code files marked revised (copied).

        Returns:
            None: Side-effects only.

        SideEffect:
            Replaces state[code_files][files_revised].

        Example:
            >>> store.set_code_files_revised(["a.py"])  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][files_revised] = ["a.py"]
        """
        self._replace_in_section("code_files", "files_revised", list(paths))

    def add_test_file_to_revise(self, file_path: str) -> None:
        """
        Append *file_path* to ``tests.files_to_revise`` (dedup).

        Args:
            file_path (str): Test file that needs another revision pass.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[tests][files_to_revise].

        Example:
            >>> store.add_test_file_to_revise("t.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[tests][files_to_revise] = [..., "t.py"]
        """
        self._append_unique_in_section("tests", "files_to_revise", file_path)

    def add_code_file_to_revise(self, file_path: str) -> None:
        """
        Append *file_path* to ``code_files.files_to_revise`` (dedup).

        Args:
            file_path (str): Code file that needs another revision pass.

        Returns:
            None: Side-effects only.

        SideEffect:
            Appends to state[code_files][files_to_revise].

        Example:
            >>> store.add_code_file_to_revise("a.py")  # doctest: +SKIP
            Return: None
            SideEffect:
                state[code_files][files_to_revise] = [..., "a.py"]
        """
        self._append_unique_in_section("code_files", "files_to_revise", file_path)
