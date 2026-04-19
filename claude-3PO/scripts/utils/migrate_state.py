#!/usr/bin/env python3
"""migrate_state.py — one-shot conversion of legacy ``state.jsonl`` → ``state.json``.

The single-session refactor swapped the JSONL session-stream layout for one
flat JSON document. The live file usually only had one line anyway, so the
migration is just "read the first parseable line, write it back as JSON."
This script is throw-away — delete it after the migration commit lands.
"""

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = SCRIPTS_DIR / "state.jsonl"
DEFAULT_JSON = SCRIPTS_DIR / "state.json"


def _read_first_entry(jsonl_path: Path) -> dict | None:
    """Return the first parseable JSON object on disk, or None.

    Args:
        jsonl_path (Path): Source state.jsonl file.

    Returns:
        dict | None: First parseable line, or None if the file is missing,
        empty, or every line is unparseable.

    Example:
        >>> _read_first_entry(Path("state.jsonl"))  # doctest: +SKIP
        Return: {'session_id': 'abc'}
    """
    # Missing source → caller decides what to do (likely: nothing to migrate).
    if not jsonl_path.exists():
        return None
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            # First good entry wins — the live file should never have more than one.
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def migrate(jsonl_path: Path, json_path: Path) -> bool:
    """Convert a single-line ``state.jsonl`` into a flat ``state.json`` body.

    Args:
        jsonl_path (Path): Source state.jsonl path.
        json_path (Path): Destination state.json path.

    Returns:
        bool: True when a migration was performed; False when there was
        nothing to migrate (missing source, empty file, all unparseable).

    SideEffect:
        Writes *json_path* with the first parseable entry from *jsonl_path*.

    Example:
        >>> migrate(Path("state.jsonl"), Path("state.json"))  # doctest: +SKIP
        Return: True
        SideEffect:
            state.json written with the legacy single-session body
    """
    entry = _read_first_entry(jsonl_path)
    # No source data → no-op so the script is safe to run repeatedly.
    if entry is None:
        return False
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(entry, separators=(",", ":")), encoding="utf-8")
    return True


def main() -> None:
    """Run the migration against the default state.jsonl/state.json paths.

    Prints a one-line summary so the operator can confirm the migration ran.

    Example:
        >>> main()  # doctest: +SKIP
    """
    if migrate(DEFAULT_JSONL, DEFAULT_JSON):
        # Confirms the migration touched a real file.
        print(f"Migrated {DEFAULT_JSONL} → {DEFAULT_JSON}", file=sys.stderr)
    else:
        # Nothing to do — print so silent failures don't look like success.
        print(f"No migration needed (source {DEFAULT_JSONL} missing or empty)",
              file=sys.stderr)


if __name__ == "__main__":
    main()
