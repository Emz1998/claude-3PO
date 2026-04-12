"""validators.py — Pure validation logic for workflow hooks.

Validators only check conditions and return a result.
They do NOT mutate state — that's the recorder's and resolver's job.

Returns:
    tuple[bool, str]:
        - (True, message) = allowed
        - raises ValueError = blocked
"""

from fnmatch import fnmatch
from urllib.parse import urlparse
from typing import Literal, Callable, cast

from constants import (
    COMMANDS_MAP,
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
    READ_ONLY_COMMANDS,
    TEST_RUN_PATTERNS,
)
from .state_store import StateStore
from .extractors import extract_skill_name, extract_agent_name, extract_md_sections
from config import Config


Result = tuple[bool, str]


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def validate_order(
    prev_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate transition based on item order."""
    if next_item not in order:
        raise ValueError(f"Invalid next item '{next_item}'")

    if prev_item is None:
        if next_item == order[0]:
            return True, f"Allowed to start with '{order[0]}'"
        raise ValueError(f"Must start with '{order[0]}', not '{next_item}'")

    if prev_item not in order:
        raise ValueError(f"Invalid previous item: '{prev_item}'")

    prev_idx = order.index(prev_item)
    next_idx = order.index(next_item)

    if next_idx < prev_idx:
        raise ValueError(f"Cannot go backwards from '{prev_item}' to '{next_item}'")

    if next_idx > prev_idx + 1:
        skipped = order[prev_idx + 1 : next_idx]
        raise ValueError(f"Must complete {skipped} before '{next_item}'")

    return True, f"Phase is allowed to transition to '{next_item}'"


def _check_safe_domain(url: str, config: Config) -> Result:
    if not url:
        raise ValueError("URL is empty")

    parsed = urlparse(url)
    host = parsed.hostname or ""

    if not host:
        raise ValueError(f"Could not parse hostname from URL: {url}")

    for domain in config.safe_domains:
        if host == domain or host.endswith("." + domain):
            return True, f"Domain '{host}' is safe"

    raise ValueError(f"Domain '{host}' is not in the safe domains list")


def _check_read_only(command: str, phase: str) -> Result:
    if any(command.startswith(cmd) for cmd in READ_ONLY_COMMANDS):
        return True, f"Read-only command allowed in phase: {phase}"

    raise ValueError(
        f"Phase '{phase}' only allows read-only commands"
        f"\nAllowed: {READ_ONLY_COMMANDS}"
    )


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — Phase
# ═══════════════════════════════════════════════════════════════════


def is_phase_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate phase transition (skill invocation)."""

    current = state.current_phase
    status = state.get_phase_status(current)
    next_phase = extract_skill_name(hook_input)

    # No phases yet — allow the first one
    if not current:
        _, message = validate_order(None, next_phase, config.main_phases)
        return True, message

    # Special case: research can run in parallel with explore
    if current == "explore" and status == "in_progress" and next_phase == "research":
        return True, "Running Research in parallel with Explore"

    # Block if current phase isn't done
    if next_phase and status != "completed":
        if next_phase == current:
            raise ValueError(
                f"Already in '{current}' phase. Complete the phase tasks instead of re-invoking the skill."
            )
        raise ValueError(
            f"Phase '{current}' is not completed. Finish it before transitioning to '{next_phase}'."
        )

    # Validate ordering
    _, message = validate_order(current, next_phase, config.main_phases)
    return True, message


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — Commands (Bash)
# ═══════════════════════════════════════════════════════════════════


def _check_phase_commands(command: str, phase: str) -> None:
    """Check command against phase-specific whitelist."""
    allowed = COMMANDS_MAP.get(phase, [])
    if allowed and not any(command.startswith(cmd) for cmd in allowed):
        raise ValueError(
            f"Command '{command}' not allowed in phase: {phase}" f"\nAllowed: {allowed}"
        )


def _check_pr_create_command(command: str) -> None:
    """Validate gh pr create includes --json for parseable output."""
    if command.startswith("gh pr create") and "--json" not in command:
        raise ValueError(
            f"PR create command must include --json flag" f"\nGot: {command}"
        )


def _check_ci_check_command(command: str) -> None:
    """Validate gh pr checks includes --json for parseable output."""
    if command.startswith("gh pr checks") and "--json" not in command:
        raise ValueError(
            f"CI check command must include --json flag" f"\nGot: {command}"
        )


def is_command_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate Bash commands against phase restrictions."""

    phase = state.current_phase
    command = hook_input.get("tool_input", {}).get("command", "")

    # Read-only phases (also allow phase-specific commands like test runners)
    if phase in config.read_only_phases:
        phase_cmds = COMMANDS_MAP.get(phase, [])
        if phase_cmds and any(command.startswith(cmd) for cmd in phase_cmds):
            return True, f"Command allowed in phase: {phase}"
        return _check_read_only(command, phase)

    # Docs phases
    if phase in config.docs_write_phases:
        return _check_read_only(command, phase)

    # Phase-specific whitelist
    _check_phase_commands(command, phase)

    # PR create must use --json
    if phase == "pr-create":
        _check_pr_create_command(command)

    # CI check must use --json
    if phase == "ci-check":
        _check_ci_check_command(command)

    return True, f"Command '{command}' allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — File Write
# ═══════════════════════════════════════════════════════════════════


def _require_agent_completed(
    agent_name: str, config: Config, state: StateStore
) -> None:
    """Block if the required agent hasn't completed yet."""
    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"{agent_name} agent must be invoked first")
    if not all(a.get("status") == "completed" for a in agents):
        raise ValueError(f"{agent_name} agent must complete before writing")


def _is_writable_phase(phase: str, config: Config) -> None:
    writable = config.code_write_phases + config.docs_write_phases
    if phase not in writable:
        raise ValueError(f"File write not allowed in phase: {phase}")


def _is_plan_path_allowed(file_path: str, config: Config) -> None:
    expected = config.plan_file_path
    if file_path != expected and not file_path.endswith(expected):
        raise ValueError(f"Writing '{file_path}' not allowed" f"\nAllowed: {expected}")


def _is_test_path_allowed(file_path: str) -> None:
    basename = file_path.rsplit("/", 1)[-1]
    if not any(fnmatch(basename, p) for p in TEST_FILE_PATTERNS):
        raise ValueError(
            f"Writing '{file_path}' not allowed"
            f"\nAllowed patterns: {TEST_FILE_PATTERNS}"
        )


def _is_code_path_allowed(file_path: str) -> None:
    if not any(file_path.endswith(ext) for ext in CODE_EXTENSIONS):
        raise ValueError(
            f"Writing '{file_path}' not allowed"
            f"\nAllowed extensions: {CODE_EXTENSIONS}"
        )


def _is_report_path_allowed(file_path: str, config: Config) -> None:
    expected = config.report_file_path
    if file_path != expected and not file_path.endswith(expected):
        raise ValueError(f"Writing '{file_path}' not allowed" f"\nAllowed: {expected}")


def is_file_write_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> Result:
    """Validate file write against phase and path restrictions."""

    phase = state.current_phase
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    _is_writable_phase(phase, config)

    if phase == "plan":
        _require_agent_completed("Plan", config, state)
        _is_plan_path_allowed(file_path, config)
    elif phase == "write-tests":
        _is_test_path_allowed(file_path)
    elif phase == "write-code":
        _is_code_path_allowed(file_path)
    elif phase == "write-report":
        _is_report_path_allowed(file_path, config)

    return True, f"File write allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — File Edit
# ═══════════════════════════════════════════════════════════════════


def _is_editable_phase(phase: str, config: Config) -> None:
    editable = config.code_edit_phases + config.docs_edit_phases
    if phase not in editable:
        raise ValueError(f"File edit not allowed in phase: {phase}")


def _is_plan_edit_allowed(file_path: str, config: Config) -> None:
    expected = config.plan_file_path
    if file_path != expected and not file_path.endswith(expected):
        raise ValueError(f"Editing '{file_path}' not allowed" f"\nAllowed: {expected}")


def _is_test_edit_allowed(file_path: str, state: StateStore) -> None:
    allowed = state.tests.get("file_paths", [])
    if file_path not in allowed:
        raise ValueError(
            f"Editing '{file_path}' not allowed" f"\nTest files in session: {allowed}"
        )


def _is_code_edit_allowed(file_path: str, state: StateStore) -> None:
    test_files = state.tests.get("file_paths", [])
    code_files = state.code_files.get("file_paths", [])

    # Allow test file edits (TDD: tests first)
    if file_path in test_files:
        return

    # Code file edit: check TDD ordering
    if file_path in code_files:
        if state.code_tests_to_revise and not state.all_code_tests_revised:
            raise ValueError(
                "Revise test files first before editing code files"
                f"\nTests to revise: {state.code_tests_to_revise}"
                f"\nTests revised: {state.code_tests_revised}"
            )
        return

    raise ValueError(
        f"Editing '{file_path}' not allowed"
        f"\nCode files in session: {code_files}"
    )


def is_file_edit_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate file edit against phase and path restrictions."""

    phase = state.current_phase
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    _is_editable_phase(phase, config)

    if phase == "plan-review":
        _is_plan_edit_allowed(file_path, config)
    elif phase == "test-review":
        _is_test_edit_allowed(file_path, state)
    elif phase == "code-review":
        _is_code_edit_allowed(file_path, state)

    return True, f"File edit allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — Agent
# ═══════════════════════════════════════════════════════════════════


def _is_parallel_research_allowed(state: StateStore, next_agent: str) -> bool:
    """Check if Research can run in parallel with an in-progress Explore."""
    explore = state.get_agent("Explore")
    return (
        explore is not None
        and explore.get("status") == "in_progress"
        and next_agent == "Research"
    )


def _is_expected_agent(next_agent: str, phase: str, config: Config) -> None:
    expected = config.get_required_agent(phase)
    if not expected:
        raise ValueError(f"No agent allowed in phase: {phase}")
    if next_agent != expected:
        raise ValueError(
            f"Agent '{next_agent}' not allowed in phase: {phase}"
            f"\nExpected: {expected}"
        )


def _is_agent_count_under_max(
    next_agent: str, phase: str, config: Config, state: StateStore
) -> None:
    max_allowed = config.get_agent_max_count(next_agent)
    actual = state.count_agents(next_agent)
    if actual >= max_allowed:
        raise ValueError(
            f"Agent '{next_agent}' at max ({max_allowed}) in phase: {phase}"
        )


def _is_revision_done(next_agent: str, phase: str, state: StateStore) -> None:
    """Block review agents if revision hasn't happened since last Fail."""
    if phase == "plan-review" and next_agent == "PlanReview":
        last = state.last_plan_review
        if last and last.get("status") == "Fail" and not state.plan_revised:
            raise ValueError("Plan must be revised before re-invoking PlanReview")

    if phase == "test-review" and next_agent == "TestReviewer":
        last = state.last_test_review
        if last and last.get("verdict") == "Fail":
            if not state.all_test_files_revised:
                raise ValueError(
                    "All test files must be revised before re-invoking TestReviewer"
                    f"\nFiles to revise: {state.test_files_to_revise}"
                    f"\nFiles revised: {state.test_files_revised}"
                )

    if phase == "code-review" and next_agent == "CodeReviewer":
        last = state.last_code_review
        if last and last.get("status") == "Fail":
            if not state.all_files_revised:
                raise ValueError(
                    "All files must be revised before re-invoking CodeReviewer"
                    f"\nFiles to revise: {state.files_to_revise}"
                    f"\nFiles revised: {state.files_revised}"
                )


def is_agent_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate agent invocation against phase and count restrictions."""

    phase = state.current_phase
    next_agent = extract_agent_name(hook_input)

    if phase == "explore" and _is_parallel_research_allowed(state, next_agent):
        return True, "Running Research in parallel with Explore"

    # Parallel case: explore is still in_progress but current_phase is research
    if next_agent == "Explore" and state.get_phase_status("explore") == "in_progress":
        phase = "explore"

    _is_expected_agent(next_agent, phase, config)
    _is_agent_count_under_max(next_agent, phase, config, state)
    _is_revision_done(next_agent, phase, state)

    return True, f"{next_agent} agent allowed in phase: {phase}"


# ═══════════════════════════════════════════════════════════════════
# PreToolUse — WebFetch
# ═══════════════════════════════════════════════════════════════════


def is_webfetch_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate that a WebFetch URL targets a safe domain."""

    url = hook_input.get("tool_input", {}).get("url", "")
    return _check_safe_domain(url, config)


# ═══════════════════════════════════════════════════════════════════
# PostToolUse — Test execution
# ═══════════════════════════════════════════════════════════════════


def _is_test_command(command: str) -> bool:
    import re

    return any(re.search(pattern, command) for pattern in TEST_RUN_PATTERNS)


def is_test_executed(command: str) -> Result:
    """Check if the command is a valid test runner."""

    if _is_test_command(command):
        return True, f"Test command recognized: '{command}'"

    raise ValueError(
        f"Command '{command}' is not a valid test command"
        f"\nExpected patterns: {TEST_RUN_PATTERNS}"
    )


# ═══════════════════════════════════════════════════════════════════
# Stop Hook — Score / verdict extraction
# ═══════════════════════════════════════════════════════════════════


def _check_score_present(confidence: int | None, quality: int | None) -> None:
    if confidence is None or quality is None:
        raise ValueError("Confidence and quality scores are required")


def _check_score_range(confidence: int, quality: int) -> None:
    if confidence not in range(1, 101):
        raise ValueError("Confidence score must be between 1 and 100")
    if quality not in range(1, 101):
        raise ValueError("Quality score must be between 1 and 100")


def scores_valid(
    content: str,
    extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
) -> tuple[bool, dict[Literal["confidence_score", "quality_score"], int]]:
    """Validate that extracted scores are present and in range (1-100)."""

    scores = extractor(content)
    confidence = scores["confidence_score"]
    quality = scores["quality_score"]

    _check_score_present(confidence, quality)
    _check_score_range(confidence, quality)  # type: ignore[arg-type]

    return True, cast(dict[Literal["confidence_score", "quality_score"], int], scores)


def verdict_valid(
    content: str,
    extractor: Callable[[str], str],
) -> tuple[bool, Literal["Pass", "Fail"]]:
    """Validate that extracted verdict is Pass or Fail."""

    verdict = extractor(content)
    if verdict not in ["Pass", "Fail"]:
        raise ValueError("Verdict must be either 'Pass' or 'Fail'")

    return True, cast(Literal["Pass", "Fail"], verdict)


def is_agent_report_valid(
    hook_input: dict,
    state: StateStore,
    score_extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
    verdict_extractor: Callable[[str], str],
) -> Result:
    """Validate the agent's report based on current phase.

    - plan-review / code-review: scores must be present and in range
    - test-review: verdict (Pass/Fail) must be present
    """

    SCORE_PHASES = ["plan-review", "code-review"]
    VERDICT_PHASES = ["test-review"]

    phase = state.current_phase
    content = hook_input.get("last_assistant_message", "")

    if not content:
        raise ValueError("Agent report is empty")

    if phase in SCORE_PHASES:
        scores_valid(content, score_extractor)
        return True, f"Agent report valid for {phase}: scores present"

    if phase in VERDICT_PHASES:
        verdict_valid(content, verdict_extractor)
        return True, f"Agent report valid for {phase}: verdict present"

    raise ValueError(f"Phase '{phase}' does not require an agent report")


# ═══════════════════════════════════════════════════════════════════
# SubagentStop — Review section validation
# ═══════════════════════════════════════════════════════════════════


def _extract_bullet_items(content: str) -> list[str]:
    """Extract bullet list items (- item) from markdown content."""
    return [
        line.lstrip("- ").strip()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    ]


def _require_section(
    sections: dict[str, str], heading: str
) -> list[str]:
    """Require a section exists and has bullet items. Returns the items."""
    if heading not in sections:
        raise ValueError(f"'{heading}' section is required")
    items = _extract_bullet_items(sections[heading])
    if not items:
        raise ValueError(f"'{heading}' section is empty — provide file paths")
    return items


def validate_review_sections(
    content: str, phase: str
) -> tuple[list[str], list[str]]:
    """Validate required sections in reviewer response.

    Returns (files_to_revise, tests_to_revise).
    - code-review: requires both "Files to revise" and "Tests to revise"
    - test-review: requires "Files to revise"
    - plan-review: no sections required
    """
    raw_sections = extract_md_sections(content, 2)
    sections = {heading: body for heading, body in raw_sections}

    if phase == "code-review":
        files = _require_section(sections, "Files to revise")
        tests = _require_section(sections, "Tests to revise")
        return files, tests

    if phase == "test-review":
        files = _require_section(sections, "Files to revise")
        return files, []

    return [], []
