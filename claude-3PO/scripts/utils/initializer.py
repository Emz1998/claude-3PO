#!/usr/bin/env python3
"""initializer.py — Pre-workflow initialization for the /implement command.

Called via bash injection in the skill .md before Claude sees the prompt.
Handles arg parsing and state initialization.

Usage:
    python3 initializer.py <workflow_type> <session_id> [args...]
    python3 initializer.py implement abc-123 SK-001
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constants import STORY_ID_PATTERN
from constants.paths import SCRIPTS_DIR
from lib.extractors import extract_frontmatter
from lib.extractors.commands import strip_flags_and_ids
from lib.state_store import StateStore
from config import Config

STATE_PATH = SCRIPTS_DIR / "state.json"


# ---------------------------------------------------------------------------
# /implement arg + frontmatter parsers
# ---------------------------------------------------------------------------


parse_frontmatter = extract_frontmatter


def parse_skip(args: str) -> list[str]:
    """
    Translate ``--skip-*`` flags in an ``/implement`` arg string into phase names.

    ``--skip-all`` is shorthand for ``--skip-explore`` and ``--skip-research``
    together. Returns the list rather than a set because downstream code
    occasionally cares about insertion order.

    Args:
        args (str): Raw arg portion of an ``/implement`` invocation.

    Returns:
        list[str]: Subset of ``["explore", "research"]``.

    Example:
        >>> parse_skip("--skip-all --tdd")
        ['explore', 'research']
        >>> parse_skip("--skip-explore add login")
        ['explore']
    """
    skip: list[str] = []
    if "--skip-explore" in args or "--skip-all" in args:
        skip.append("explore")
    if "--skip-research" in args or "--skip-all" in args:
        skip.append("research")
    return skip


def parse_story_id(args: str) -> str | None:
    """
    Pull the first story ID (e.g. ``US-001``) from an ``/implement`` arg string.

    Args:
        args (str): Raw arg portion of an ``/implement`` invocation.

    Returns:
        str | None: Matched story ID, or ``None`` if none is present.

    Example:
        >>> parse_story_id("US-001 add login")
        'US-001'
    """
    match = re.search(STORY_ID_PATTERN, args)
    return match.group(1) if match else None


parse_instructions = strip_flags_and_ids


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


def build_initial_state(workflow_type: str, session_id: str, args: str) -> dict:
    """Build the initial state dict for an ``implement`` workflow.

    All review/revision lists start empty so resolvers can append without
    checking for the key.

    Args:
        workflow_type (str): The workflow identifier — currently only
            ``"implement"``; recorded verbatim for downstream branching.
        session_id (str): Hook session id.
        args (str): Joined command args; parsed for ``--tdd``, ``--test``,
            ``--skip``, story id, and instruction tail.

    Returns:
        dict: Fresh implement state ready for ``StateStore.reinitialize``.

    Example:
        >>> s = build_initial_state("implement", "sess-1", "--tdd")
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
        "validation_result": None,
        "report_written": False,
    }


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

    Also archives the previous plan so the fresh session starts clean.
    ``--takeover`` short-circuits when the file already has content (the
    existing state is preserved verbatim); every other path overwrites with
    a fresh dict from :func:`build_initial_state`.

    Args:
        workflow_type (str): Workflow identifier (currently ``"implement"``).
        session_id (str): Hook session id; recorded inside the state body.
        args (str): Joined command-line args (flags + story id + instructions).
        state_path (Path): Path to the single state.json store. Defaults to
            the module-level STATE_PATH; overridable for tests.

    Example:
        >>> initialize("implement", "sess-abc", "--test")  # doctest: +SKIP
    """
    # --takeover with existing content: preserve in place, no reinit.
    if "--takeover" in args and _has_existing_state(state_path):
        return

    store = StateStore(state_path)

    # Archive the prior plan before overwriting.
    archive_plan(Config())

    state = build_initial_state(workflow_type, session_id, args)
    store.reinitialize(state)


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
