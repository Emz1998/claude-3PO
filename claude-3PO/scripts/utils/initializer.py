#!/usr/bin/env python3
"""initializer.py — Pre-workflow initialization for /implement and /build commands.

Called via bash injection in skill .md before Claude sees the prompt.
Handles arg parsing and state initialization.

Usage:
    python3 initializer.py <workflow_type> <session_id> [args...]
    python3 initializer.py implement abc-123 SK-001
    python3 initializer.py build abc-123 --tdd build a login form
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constants import STORY_ID_PATTERN
from lib.state_store import StateStore
from lib import subprocess_agents
from config import Config

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


# ---------------------------------------------------------------------------
# /build arg + frontmatter parsers (formerly lib/parser.py)
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> dict[str, str]:
    """
    Extract YAML frontmatter key-value pairs from a markdown string.

    Only handles the simple ``key: value`` shape — nested YAML, lists, or
    multi-line values are not supported because the workflow frontmatter
    schema is intentionally flat. Missing or malformed frontmatter returns
    ``{}`` so callers can blindly ``.get(...)`` without exception handling.

    Args:
        content (str): Markdown text potentially starting with a ``---`` block.

    Returns:
        dict[str, str]: Frontmatter keys → values; empty dict if absent.

    Example:
        >>> parse_frontmatter("---\\nsession_id: abc\\n---\\n# Title")
        {'session_id': 'abc'}
    """
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip()
    return fm


def parse_skip(args: str) -> list[str]:
    """
    Translate ``--skip-*`` flags in a ``/build`` arg string into phase names.

    ``--skip-all`` is shorthand for ``--skip-explore`` and ``--skip-research``
    together; ``--skip-vision`` and ``--skip-clarify`` stand alone. Returns
    the list rather than a set because downstream code occasionally cares
    about insertion order.

    Args:
        args (str): Raw arg portion of a ``/build`` invocation.

    Returns:
        list[str]: Subset of ``["clarify", "explore", "research", "vision"]``.

    Example:
        >>> parse_skip("--skip-all --tdd")
        ['explore', 'research']
        >>> parse_skip("--skip-clarify build login")
        ['clarify']
    """
    skip: list[str] = []
    if "--skip-clarify" in args:
        skip.append("clarify")
    if "--skip-explore" in args or "--skip-all" in args:
        skip.append("explore")
    if "--skip-research" in args or "--skip-all" in args:
        skip.append("research")
    if "--skip-vision" in args:
        skip.append("vision")
    return skip


def parse_story_id(args: str) -> str | None:
    """
    Pull the first story ID (e.g. ``US-001``) from a ``/build`` arg string.

    Args:
        args (str): Raw arg portion of a ``/build`` invocation.

    Returns:
        str | None: Matched story ID, or ``None`` if none is present.

    Example:
        >>> parse_story_id("US-001 add login")
        'US-001'
    """
    match = re.search(STORY_ID_PATTERN, args)
    return match.group(1) if match else None


def parse_instructions(args: str) -> str:
    """
    Strip flags and story IDs from a ``/build`` arg string, returning the prose.

    The whitelist of recognized flags is hard-coded here (rather than imported
    from a constant) so adding a new ``/build`` flag must be a deliberate edit
    in one obvious place.

    Args:
        args (str): Raw arg portion of a ``/build`` invocation.

    Returns:
        str: Cleaned instruction text with surrounding whitespace stripped.

    Example:
        >>> parse_instructions("US-001 --tdd add login")
        'add login'
    """
    flags = [
        "--skip-clarify", "--skip-explore", "--skip-research", "--skip-vision", "--skip-all",
        "--tdd", "--reset", "--takeover", "--test",
    ]
    text = re.sub(STORY_ID_PATTERN, "", args)
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


# ---------------------------------------------------------------------------
# Plan archival (formerly lib/archiver.py)
# ---------------------------------------------------------------------------


def archive_plan(config: Config) -> None:
    """
    Archive the existing ``latest-plan.md`` before starting a new workflow.

    The archive filename embeds today's date and the *previous* workflow's
    ``session_id`` (read from the plan's frontmatter) so each archived plan is
    traceable back to the run that produced it. If the plan file does not exist
    the call is a no-op — first-ever runs have nothing to archive.

    Args:
        config (Config): Project config providing ``plan_file_path`` and
            ``plan_archive_dir``.

    Returns:
        None: Side-effects only — copies the file and deletes the original.

    Example:
        >>> archive_plan(Config())  # doctest: +SKIP
    """
    plan_path = Path(config.plan_file_path)
    if not plan_path.exists():
        return

    content = plan_path.read_text()
    fm = parse_frontmatter(content)
    session_id = fm.get("session_id", "unknown")
    date = datetime.now().strftime("%Y-%m-%d")

    archive_dir = Path(config.plan_archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"plan_{date}_{session_id}.md"
    shutil.copy2(plan_path, archive_dir / archive_name)
    plan_path.unlink()


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------


def _build_specs_state(session_id: str, args: str) -> dict:
    """Build the initial state dict for a ``specs`` workflow.

    Specs state tracks four documents (product_vision, decisions,
    architecture, backlog) rather than the per-task plan/test/code
    layout used by build workflows. Each ``docs`` entry is a uniform
    ``{written, path}`` pair so resolvers can check completion the
    same way for every doc type.

    Args:
        session_id (str): Hook session id; becomes ``state.session_id``.
        args (str): Joined command args; parsed for ``--skip`` and the
            free-form instruction tail.

    Returns:
        dict: Fresh specs-workflow state ready for ``StateStore.reinitialize``.

    Example:
        >>> s = _build_specs_state("sess-1", "")
        >>> s["workflow_type"]
        'specs'
    """
    skip = parse_skip(args)
    test_mode = "--test" in args
    instructions = parse_instructions(args)
    return {
        "session_id": session_id,
        "workflow_active": True,
        "status": "in_progress",
        "workflow_type": "specs",
        "test_mode": test_mode,
        "phases": [],
        "agents": [],
        "skip": skip,
        "instructions": instructions,
        "docs": {
            "product_vision": {"written": False, "path": ""},
            "decisions": {"written": False, "path": ""},
            "architecture": {"written": False, "path": ""},
            "backlog": {"written": False, "md_path": "", "json_path": ""},
        },
    }


def _build_build_state(workflow_type: str, session_id: str, args: str) -> dict:
    """Build the initial state dict for a ``build`` or ``implement`` workflow.

    The two workflow types share the same state shape; ``workflow_type`` is
    stored verbatim so resolvers can branch on it (e.g. ``implement`` requires
    project-task subtasks rather than flat tasks). All review/revision lists
    start empty so resolvers can append without checking for the key.

    Args:
        workflow_type (str): Either ``"build"`` or ``"implement"``.
        session_id (str): Hook session id.
        args (str): Joined command args; parsed for ``--tdd``, ``--test``,
            ``--skip``, story id, and instruction tail.

    Returns:
        dict: Fresh build/implement state ready for ``StateStore.reinitialize``.

    Example:
        >>> s = _build_build_state("build", "sess-1", "--tdd")
        >>> s["tdd"]
        True
    """
    skip = parse_skip(args)
    tdd = "--tdd" in args
    test_mode = "--test" in args
    story_id = parse_story_id(args)
    instructions = parse_instructions(args)

    return {
        "session_id": session_id,
        "workflow_active": True,
        "status": "in_progress",
        "workflow_type": workflow_type,
        "test_mode": test_mode,
        "phases": [],
        "tdd": tdd,
        "story_id": story_id,
        "skip": skip,
        "instructions": instructions,
        "agents": [],
        "plan": {
            "file_path": None,
            "written": False,
            "revised": None,
            "reviews": [],
        },
        "tasks": [],
        "tests": {
            "file_paths": [],
            "executed": False,
            "reviews": [],
            "files_to_revise": [],
            "files_revised": [],
        },
        "code_files_to_write": [],
        "code_files": {
            "file_paths": [],
            "reviews": [],
            "files_to_revise": [],
            "files_revised": [],
        },
        "quality_check_result": None,
        "pr": {"status": "pending", "number": None},
        "ci-check": {"status": "pending", "results": []},
        "report_written": False,
    }


def build_initial_state(workflow_type: str, session_id: str, args: str) -> dict:
    """Dispatch to the per-workflow state builder.

    Args:
        workflow_type (str): One of ``"specs"``, ``"build"``, ``"implement"``.
            Anything other than ``"specs"`` is treated as a build-style workflow.
        session_id (str): Hook session id.
        args (str): Joined command-line args.

    Returns:
        dict: A fresh state dict for the chosen workflow type.

    Example:
        >>> s = build_initial_state("specs", "sess-1", "")
        >>> s["workflow_type"]
        'specs'
    """
    if workflow_type == "specs":
        return _build_specs_state(session_id, args)
    return _build_build_state(workflow_type, session_id, args)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def initialize(
    workflow_type: str,
    session_id: str,
    args: str,
    state_path: Path = STATE_PATH,
) -> None:
    """Initialize state for a new workflow session in single-file ``state.json``.

    For non-specs workflows, also archives the previous plan so the fresh
    session starts clean. ``--takeover`` short-circuits when the file already
    has content (the existing state is preserved verbatim); every other path
    overwrites with a fresh dict from :func:`build_initial_state`.

    Args:
        workflow_type (str): ``"specs"``, ``"build"``, or ``"implement"``.
        session_id (str): Hook session id; recorded inside the state body.
        args (str): Joined command-line args (flags + story id + instructions).
        state_path (Path): Path to the single state.json store. Defaults to
            the module-level STATE_PATH; overridable for tests.

    Example:
        >>> initialize("specs", "sess-abc", "--test")  # doctest: +SKIP
    """
    # --takeover with existing content: preserve in place, no reinit.
    if "--takeover" in args and _has_existing_state(state_path):
        return

    store = StateStore(state_path)

    if workflow_type == "specs":
        state = build_initial_state(workflow_type, session_id, args)
        store.reinitialize(state)
        return

    # Non-specs workflows: archive the prior plan before overwriting.
    archive_plan(Config())

    state = build_initial_state(workflow_type, session_id, args)
    store.reinitialize(state)
    if workflow_type == "build":
        _seed_clarify_phase(store, args)


def _has_existing_state(state_path: Path) -> bool:
    """Return True iff *state_path* exists and has non-empty body content.

    Used by ``--takeover`` to decide whether to preserve the file or fall
    through to a fresh init. Empty files are treated as "no state".

    Args:
        state_path (Path): The single-file state.json path.

    Returns:
        bool: True when the file exists and has at least one non-whitespace char.

    Example:
        >>> _has_existing_state(Path("/tmp/state.json"))  # doctest: +SKIP
        Return: False
    """
    # Existence + non-empty body — both required so --takeover doesn't preserve nothing.
    if not state_path.exists():
        return False
    return bool(state_path.read_text(encoding="utf-8").strip())


def _seed_clarify_phase(store: StateStore, args: str) -> None:
    """Add the ``clarify`` phase to fresh build state, gated by headless review.

    Skips the headless call entirely when ``--skip-clarify`` is in args
    (clarify gets ``status="skipped"``). Otherwise runs
    ``subprocess_agents.run_initial`` against the user's prompt and either
    marks clarify skipped (verdict=clear) or in-progress with the captured
    headless session id (verdict=vague).

    Args:
        store (StateStore): The freshly-initialized state store.
        args (str): Joined command-line args (parsed for ``--skip-clarify``
            and the user's instruction tail).

    Example:
        >>> _seed_clarify_phase(store, "--skip-clarify add login")  # doctest: +SKIP
    """
    if "--skip-clarify" in args:
        _add_clarify(store, status="skipped")
        return
    prompt = parse_instructions(args)
    sid, verdict = subprocess_agents.run_initial(prompt)
    if verdict == "clear":
        _add_clarify(store, status="skipped")
    else:
        _add_clarify(store, status="in_progress", session_id=sid)


def _add_clarify(store: StateStore, status: str, session_id: str = "") -> None:
    """Append the clarify phase entry with the given status (and optional session).

    Args:
        store (StateStore): Target state store.
        status (str): One of ``"skipped"`` or ``"in_progress"``.
        session_id (str): Headless session id; ignored when status is skipped.

    Example:
        >>> _add_clarify(store, "in_progress", "sess_x")  # doctest: +SKIP
    """
    def _add(d: dict) -> None:
        entry = {"name": "clarify", "status": status}
        if status == "in_progress":
            entry["headless_session_id"] = session_id
            entry["iteration_count"] = 0
        d.setdefault("phases", []).append(entry)

    store.update(_add)


def main() -> None:
    """Script entry point — parses ``sys.argv`` and calls :func:`initialize`.

    Prints a usage line to stderr and returns (exit 0) when too few
    arguments are supplied; the bash skill wrapper treats that as a
    no-op rather than failing the user's command.

    Example:
        >>> main()  # doctest: +SKIP
    """
    if len(sys.argv) < 3:
        print(
            "Usage: initializer.py <workflow_type> <session_id> [args...]",
            file=sys.stderr,
        )
        return

    workflow_type = sys.argv[1]
    session_id = sys.argv[2]
    args = " ".join(sys.argv[3:])

    initialize(workflow_type, session_id, args)


if __name__ == "__main__":
    main()
