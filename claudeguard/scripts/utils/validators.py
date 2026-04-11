"""validators.py — Pure validation logic for workflow hooks.

Validators only check conditions and return a result.
They do NOT mutate state — that's the recorder's and resolver's job.

Returns:
    tuple[bool, str]:
        - (True, message) = allowed
        - raises ValueError = blocked
"""

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
    next_phase = hook_input.get("tool_input", {}).get("skill", "")

    # No phases yet — allow the first one
    if not current:
        _, message = validate_order(None, next_phase, config.main_phases)
        return True, message

    # Special case: research can run in parallel with explore
    if current == "explore" and status == "in_progress" and next_phase == "research":
        return True, "Running Research in parallel with Explore"

    # Block if current phase isn't done
    if next_phase and status != "completed":
        raise ValueError(f"Phase '{current}' is not completed")

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
            f"Command '{command}' not allowed in phase: {phase}"
            f"\nAllowed: {allowed}"
        )


def _check_pr_create_command(command: str) -> None:
    """Validate gh pr create includes --json for parseable output."""
    if command.startswith("gh pr create") and "--json" not in command:
        raise ValueError(
            f"PR create command must include --json flag"
            f"\nGot: {command}"
        )


def _check_ci_check_command(command: str) -> None:
    """Validate gh pr checks includes --json for parseable output."""
    if command.startswith("gh pr checks") and "--json" not in command:
        raise ValueError(
            f"CI check command must include --json flag"
            f"\nGot: {command}"
        )


def is_command_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate Bash commands against phase restrictions."""

    phase = state.current_phase
    command = hook_input.get("tool_input", {}).get("command", "")

    # Read-only phases
    if phase in config.read_only_phases:
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


def _is_writable_phase(phase: str, config: Config) -> None:
    writable = config.code_write_phases + config.docs_write_phases
    if phase not in writable:
        raise ValueError(f"File write not allowed in phase: {phase}")


def _is_plan_path_allowed(file_path: str, config: Config) -> None:
    if file_path != config.plan_file_path:
        raise ValueError(
            f"Writing '{file_path}' not allowed" f"\nAllowed: {config.plan_file_path}"
        )


def _is_test_path_allowed(file_path: str) -> None:
    if not any(file_path.endswith(p.lstrip("*")) for p in TEST_FILE_PATTERNS):
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
    if file_path != config.report_file_path:
        raise ValueError(
            f"Writing '{file_path}' not allowed" f"\nAllowed: {config.report_file_path}"
        )


def is_file_write_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> Result:
    """Validate file write against phase and path restrictions."""

    phase = state.current_phase
    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    _is_writable_phase(phase, config)

    if phase == "plan":
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
    if file_path != config.plan_file_path:
        raise ValueError(
            f"Editing '{file_path}' not allowed" f"\nAllowed: {config.plan_file_path}"
        )


def _is_test_edit_allowed(file_path: str, state: StateStore) -> None:
    allowed = state.tests.get("file_paths", [])
    if file_path not in allowed:
        raise ValueError(
            f"Editing '{file_path}' not allowed" f"\nTest files in session: {allowed}"
        )


def _is_code_edit_allowed(file_path: str, state: StateStore) -> None:
    allowed = state.code_files.get("file_paths", [])
    if file_path not in allowed:
        raise ValueError(
            f"Editing '{file_path}' not allowed" f"\nCode files in session: {allowed}"
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


def is_agent_allowed(hook_input: dict, config: Config, state: StateStore) -> Result:
    """Validate agent invocation against phase and count restrictions."""

    phase = state.current_phase
    next_agent = hook_input.get("tool_input", {}).get("subagent_type", "")

    if phase == "explore" and _is_parallel_research_allowed(state, next_agent):
        return True, "Running Research in parallel with Explore"

    _is_expected_agent(next_agent, phase, config)
    _is_agent_count_under_max(next_agent, phase, config, state)

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
