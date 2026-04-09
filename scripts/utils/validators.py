"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

from urllib.parse import urlparse
from typing import Literal, Any, TypeVar, Callable

import tomllib


from constants import (
    COMMANDS_MAP,
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
    READ_ONLY_COMMANDS,
)

from utils.extractors import extract_scores
from constants import TEST_RUN_PATTERNS

from models import *
from .state_store import StateStore
from .helpers import validate_order, is_revision_needed
from config import Config


def load_config() -> dict[str, Any]:
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

    return config


def is_safe_domain(url: str, config: Config) -> str:
    safe_domains = config.safe_domains
    if not url:
        raise ValueError("URL is empty")

    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host:
        raise ValueError(f"Could not parse hostname from URL: {url}")

    for domain in safe_domains:
        if host == domain or host.endswith("." + domain):
            return f"Domain '{host}' is safe"

    raise ValueError(f"Domain '{host}' is not in the safe domains list")


def is_webfetch_allowed(
    state: StateStore, hook_input: dict, config: Config
) -> tuple[Literal["allow", "skip"], str]:
    """Validate that a WebFetch URL targets a safe domain."""
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "WebFetch":
        return "skip", "Skipping, not a WebFetch tool"

    url = hook_input.get("tool_input", {}).get("url", "")
    return "allow", is_safe_domain(url, config)


def is_command_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> tuple[Literal["allow", "skip"], str]:
    """Validate the command."""
    phase = state.current_phase
    tool_name = hook_input.get("tool_name", "")
    command = hook_input.get("tool_input", {}).get("command", "")

    docs_only_phases = config.docs_write_phases
    read_only_phases = config.read_only_phases

    read_only_commands = READ_ONLY_COMMANDS

    if phase in read_only_phases and command not in read_only_commands:
        raise ValueError(
            f"Phase {phase} is read-only\nAllowed commands in this phase: {read_only_commands}"
        )

    if phase in docs_only_phases and command not in read_only_commands:
        raise ValueError(
            f"Phase {phase} is a documentation phase"
            f"\nAllowed commands in this phase: {read_only_commands}"
            f"\nUse Write tool if you want to write or edit a document"
        )

    if tool_name != "Bash":
        return "skip", "Skipping, not a Bash tool"

    if not any(command.startswith(cmd) for cmd in COMMANDS_MAP[phase]):
        allowed_commands = COMMANDS_MAP[phase]
        raise ValueError(
            f"Invalid PR command: {command} for phase: {phase}\nAllowed commands in this phase: {allowed_commands}"
        )

    return "allow", f"PR command {command} is allowed in phase: {phase}"


def is_file_write_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> tuple[Literal["allow", "skip"], str]:
    """Validate the code files. If extensions are not supported, raise an error."""
    phase = state.current_phase
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    code_write_phases = config.code_write_phases
    docs_write_phases = config.docs_write_phases

    if tool_name != "Write":
        return "skip", "Skipping, not a Write tool"

    file_path = tool_input.get("file_path", "")

    if phase not in code_write_phases and phase not in docs_write_phases:
        raise ValueError(f"File write not allowed in phase: {phase}")

    if phase == "plan":
        if file_path != config.plan_file_path:
            raise ValueError(
                f"Writing in '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed path: {config.plan_file_path}"
            )

    if phase == "write-tests":
        if not any(
            file_path.match(test_pattern) for test_pattern in TEST_FILE_PATTERNS
        ):
            raise ValueError(
                f"Writing test file in '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed patterns: {TEST_FILE_PATTERNS}"
            )

    if phase == "write-code":
        if not any(file_path.endswith(ext) for ext in CODE_EXTENSIONS):
            raise ValueError(
                f"Writing code file in '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed extensions: {CODE_EXTENSIONS}"
            )

    if phase == "write-report":
        if file_path != config.report_file_path:
            raise ValueError(
                f"Writing report file in '{file_path}' is not allowed in phase: {phase}"
                f"\nAllowed path: {config.report_file_path}"
            )

    return "allow", f"File write allowed in phase: {phase}"


def is_file_edit_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> tuple[Literal["allow", "skip"], str]:
    """Validate the code files. If extensions are not supported, raise an error."""
    phase = state.current_phase
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    code_edit_phases = config.code_edit_phases
    docs_edit_phases = config.docs_edit_phases

    test_file_paths = state.tests.get("file_paths", [])
    code_file_paths = state.code_files.get("file_paths", [])

    if tool_name != "Edit":
        return "skip", "Skipping, not an Edit tool"

    file_path = tool_input.get("file_path", "")

    if phase not in code_edit_phases and phase not in docs_edit_phases:
        raise ValueError(f"File edit not allowed in phase: {phase}")

    if phase == "plan-review":
        if file_path != config.plan_file_path:
            raise ValueError(
                f"Editing '{file_path}' is not allowed. {file_path} does not exist or not written in this session"
                f"\nAllowed path: {config.plan_file_path}"
            )

    if phase == "test-review":
        if file_path not in test_file_paths:
            raise ValueError(
                f"Editing '{file_path}' is not allowed. {file_path} does not exist or not written in this session"
                f"\nTest files in this session: {test_file_paths}"
            )

    if phase == "code-review":
        if file_path not in code_file_paths:
            raise ValueError(
                f"Editing '{file_path}' is not allowed. {file_path} does not exist or not written in this session"
                f"\nCode files in this session: {code_file_paths}"
            )

    return "allow", f"File edit allowed in phase: {phase}"


def is_agent_allowed(
    hook_input: dict, config: Config, state: StateStore
) -> tuple[Literal["allow", "skip"], str]:
    """Validate the agent. If the agent is not allowed, raise an error."""
    phase = state.current_phase
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Agent":
        return "skip", "Skipping, not an Agent tool"

    explore_agent_status = state.get_agent("explore").get("status", "")
    next_agent = tool_input.get("agent_type", "")
    expected_agent = config.get_required_agent(phase)

    if explore_agent_status == "in_progress" and next_agent == "Research":
        return "allow", "Running Research in parallel with Explore"

    if not expected_agent:
        raise ValueError(f"No agent allowed in phase: {phase}")

    if next_agent != expected_agent:
        raise ValueError(
            f"Agent '{next_agent}' is not allowed in phase: {phase}"
            f"\nExpected: {expected_agent}"
        )

    max_allowed = config.get_agent_max_count(next_agent)
    actual = state.count_agents(next_agent)
    if actual >= max_allowed:
        raise ValueError(
            f"Agent '{next_agent}' already at max ({max_allowed}) in phase: {phase}"
        )

    return "allow", f"{next_agent} agent is allowed in phase: {phase}"


T = TypeVar("T", bound=Literal["in_progress", "completed"])


def is_phase_allowed(state: StateStore, hook_input: dict, config: Config) -> str:
    """Validate the phase(skill). If the phase is not allowed, raise an error. Note: Phase is equivalent to hook skill"""
    current_phase = state.current_phase

    current_phase_status = state.get_phase_status(current_phase)

    next_phase = hook_input.get("tool_input", {}).get("skill", "")

    if current_phase == "explore" and current_phase_status == "in_progress":
        if next_phase == "research":
            return "Running Research in parallel with Explore"

    if next_phase and current_phase_status != "completed":
        raise ValueError(f"Phase '{current_phase}' is not completed")

    allowed_message = validate_order(current_phase, next_phase, config.main_phases)

    return allowed_message


def is_agent_response_format_valid(
    hook_input: dict,
    state: StateStore,
    config: Config,
    extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
) -> str:
    """Validate the agent response format."""

    if state.current_phase not in ["plan-review", "test-review", "code-review"]:
        return "Skipping, not a review phase"

    content = hook_input.get("last_assistant_message", "")

    scores = extractor(content)

    confidence_score = scores["confidence_score"]
    quality_score = scores["quality_score"]

    if confidence_score is None or quality_score is None:
        raise ValueError(
            "Confidence and quality scores are required as the agent response"
        )

    if confidence_score not in range(1, 101):
        raise ValueError("Confidence score must be between 1 and 100")

    if quality_score not in range(1, 101):
        raise ValueError("Quality score must be between 1 and 100")

    return f"Agent response format is valid"


def is_explore_phase_completed(config: Config, state: StateStore) -> str:
    """Check all Explore agents have completed."""
    agent_name = config.get_required_agent("explore")
    if not agent_name:
        return "No agent required for explore phase"

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agents found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Explore not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    return f"Explore completed: all {len(agents)} '{agent_name}' agent(s) done"


def is_research_phase_completed(config: Config, state: StateStore) -> str:
    """Check all Research agents have completed."""
    agent_name = config.get_required_agent("research")
    if not agent_name:
        return "No agent required for research phase"

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agents found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Research not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    return f"Research completed: all {len(agents)} '{agent_name}' agent(s) done"


def is_content_valid(
    content: str,
    extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
) -> bool:
    scores = extractor(content)

    confidence_score = scores["confidence_score"]
    quality_score = scores["quality_score"]

    if confidence_score is None or quality_score is None:
        raise ValueError("Confidence and quality scores are required")

    return True


def is_plan_phase_completed(config: Config, state: StateStore) -> str:
    """Check the plan has been written to the expected file path."""
    plan = state.plan
    if not plan.get("written"):
        raise ValueError("Plan has not been written yet")

    file_path = plan.get("file_path", "")
    expected = config.plan_file_path
    if file_path != expected:
        raise ValueError(f"Plan written to '{file_path}' but expected '{expected}'")

    return f"Plan completed: written to '{file_path}'"


def is_plan_review_phase_completed(config: Config, state: StateStore) -> str:
    """Check the plan review agent was invoked and scores meet thresholds."""
    agent_name = config.get_required_agent("plan-review")
    if not agent_name:
        raise ValueError("No agent configured for plan-review phase")

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agent found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Plan review not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    review = state.plan.get("review", {})
    scores = review.get("scores") or {}
    confidence = scores.get("confidence_score", 0)
    quality = scores.get("quality_score", 0)

    is_revision_needed("plan", confidence, quality, config)

    return f"Plan review completed: confidence {confidence}, quality {quality}"


def is_write_test_phase_completed(state: StateStore) -> str:
    """Check that test files have been written."""
    tests = state.tests
    file_paths = tests.get("file_paths", [])

    if not file_paths:
        raise ValueError("No test files have been written")

    return f"Write tests completed: {len(file_paths)} test file(s) written"


def is_test_review_phase_completed(state: StateStore) -> str:
    """Check that test review result is Pass."""
    tests = state.tests
    review_result = tests.get("review_result")

    if review_result is None:
        raise ValueError("Test review has not been performed yet")

    if review_result != "Pass":
        raise ValueError(f"Test review result is '{review_result}', expected 'Pass'")

    return "Test review completed: result is Pass"


def is_write_code_phase_completed(state: StateStore) -> str:
    """Check that all expected code files have been written."""
    to_write = set(state.code_files_to_write)
    written = set(state.code_files.get("file_paths", []))

    if not to_write:
        raise ValueError("No code files expected to be written")

    missing = to_write - written
    if missing:
        raise ValueError(f"Code files not yet written: {sorted(missing)}")

    return f"Write code completed: {len(written)} code file(s) written"


def is_code_review_phase_completed(config: Config, state: StateStore) -> str:
    """Check the code reviewer agent was invoked and scores meet thresholds."""
    agent_name = config.get_required_agent("code-review")
    if not agent_name:
        raise ValueError("No agent configured for code-review phase")

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agent found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Code review not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    review = state.code_files.get("review", {})
    scores = review.get("scores") or {}
    confidence = scores.get("confidence_score", 0)
    quality = scores.get("quality_score", 0)

    is_revision_needed("code", confidence, quality, config)

    return f"Code review completed: confidence {confidence}, quality {quality}"


def is_quality_check_phase_completed(config: Config, state: StateStore) -> str:
    """Check QA specialist was invoked and quality check result is Pass."""
    agent_name = config.get_required_agent("quality-check")
    if not agent_name:
        raise ValueError("No agent configured for quality-check phase")

    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"No '{agent_name}' agent found in state")

    pending = [a for a in agents if a.get("status") != "completed"]
    if pending:
        raise ValueError(
            f"Quality check not complete: {len(pending)} '{agent_name}' agent(s) still in progress"
        )

    result = state.quality_check_result
    if result is None:
        raise ValueError("Quality check has not been performed yet")

    if result != "Pass":
        raise ValueError(f"Quality check result is '{result}', expected 'Pass'")

    return "Quality check completed: result is Pass"


def is_pr_create_phase_completed(state: StateStore) -> str:
    """Check that PR has been created."""
    status = state.pr_status
    if status != "created":
        raise ValueError(f"PR status is '{status}', expected 'created'")

    return "PR create completed: status is 'created'"


def is_ci_check_phase_completed(state: StateStore) -> str:
    """Check that CI has passed."""
    status = state.ci_status
    if status != "passed":
        raise ValueError(f"CI status is '{status}', expected 'passed'")

    return "CI check completed: status is 'passed'"


def is_test_executed(command: str) -> str:
    """Check if the command is a valid test command."""
    import re

    for pattern in TEST_RUN_PATTERNS:
        if re.search(pattern, command):
            return f"Test command recognized: '{command}'"

    raise ValueError(
        f"Command '{command}' is not a valid test command"
        f"\nExpected patterns: {TEST_RUN_PATTERNS}"
    )
