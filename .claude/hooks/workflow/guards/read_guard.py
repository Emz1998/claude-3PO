"""read_guard.py — Plan-scoped file read enforcement during coding phases.

Only enforced during: write-tests, write-code, validate, ci-check, report.
Reads are constrained to three sources:
  1. CODEBASE.md — project root context file
  2. Plan-listed files — from ## Files to Modify / ## Critical Files
  3. Previously written files — tracked via files_written state key

Test files are also allowed during write-tests phase.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workflow.config import CODING_PHASES, CODEBASE_MD, TEST_PATH_PATTERNS
from workflow.session_store import SessionStore


def _is_codebase_md(file_path: str) -> bool:
    """Check if file is CODEBASE.md at the project root."""
    normalized = file_path.replace("\\", "/").lstrip("./")
    return normalized == CODEBASE_MD or Path(file_path).name == CODEBASE_MD


def _is_test_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return any(p.search(normalized) for p in TEST_PATH_PATTERNS)


def _parse_plan_files(plan_content: str) -> list[str]:
    """Extract file paths from plan's 'Files to Modify' or 'Critical Files' section."""
    files: list[str] = []

    # Find the relevant section
    section_pattern = re.compile(
        r"^##\s+(Files to Modify|Critical Files)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = section_pattern.search(plan_content)
    if not match:
        return files

    section_start = match.end()
    # Find next ## section or end of string
    next_section = re.search(r"^##\s+", plan_content[section_start:], re.MULTILINE)
    section_end = (
        section_start + next_section.start() if next_section else len(plan_content)
    )
    section_content = plan_content[section_start:section_end]

    # Extract backtick-quoted paths from table cells
    backtick_paths = re.findall(r"`([^`]+\.[a-zA-Z]+)`", section_content)
    for path in backtick_paths:
        # Strip leading ./ or /
        clean = path.lstrip("./")
        if "/" in clean or "." in clean:
            files.append(clean)
            # Also add with leading paths stripped
            parts = clean.split("/")
            files.append(parts[-1])

    return list(set(files))


def _load_plan_files(state: dict) -> list[str] | None:
    """Load plan files from cache or parse from plan file. Returns None if no plan."""
    cached = state.get("plan_files_cache")
    if cached is not None:
        return cached

    plan_file = state.get("plan_file")
    if not plan_file:
        return None

    try:
        content = Path(plan_file).read_text()
    except (FileNotFoundError, OSError):
        return None

    return _parse_plan_files(content)


def _is_in_plan(file_path: str, plan_files: list[str]) -> bool:
    """Check if file_path matches any plan-listed file."""
    normalized = file_path.replace("\\", "/").lstrip("./")
    filename = Path(file_path).name

    for allowed in plan_files:
        allowed_norm = allowed.replace("\\", "/").lstrip("./")
        if (
            normalized == allowed_norm
            or normalized.endswith("/" + allowed_norm)
            or allowed_norm.endswith("/" + normalized)
            or filename == Path(allowed).name
        ):
            return True
    return False


def _is_previously_written(file_path: str, state: dict) -> bool:
    """Check if file was previously written/edited in this session."""
    files_written = state.get("files_written", [])
    if not files_written:
        return False

    normalized = file_path.replace("\\", "/").lstrip("./")
    filename = Path(file_path).name

    for written in files_written:
        written_norm = written.replace("\\", "/").lstrip("./")
        if (
            normalized == written_norm
            or normalized.endswith("/" + written_norm)
            or written_norm.endswith("/" + normalized)
            or filename == Path(written).name
        ):
            return True
    return False


def validate(hook_input: dict, store: SessionStore) -> tuple[str, str]:
    """Validate a Read tool invocation against the three-source constraint.

    Returns ("allow", "") or ("block", reason).
    Only enforced during coding phases (write-tests, write-code, validate, ci-check, report).
    """
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    phase = state.get("phase", "")
    if phase not in CODING_PHASES:
        return "allow", ""

    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    # Source 1: CODEBASE.md is always allowed
    if _is_codebase_md(file_path):
        return "allow", ""

    # During write-tests, test files are always allowed
    if phase == "write-tests" and _is_test_file(file_path):
        return "allow", ""

    # Source 2: Plan-listed files
    plan_files = _load_plan_files(state)
    if plan_files is None:
        # No plan file configured — allow all reads
        return "allow", ""

    # Cache plan files if not cached
    if state.get("plan_files_cache") is None:
        store.set("plan_files_cache", plan_files)

    if _is_in_plan(file_path, plan_files):
        return "allow", ""

    # Source 3: Previously written files
    if _is_previously_written(file_path, state):
        return "allow", ""

    return (
        "block",
        f"Blocked: file '{file_path}' is not in CODEBASE.md, plan, or previously written files during '{phase}' phase. Add it to the plan or read an allowed file.",
    )
