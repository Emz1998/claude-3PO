"""blockers.py — Pure check functions that raise ValueError when a condition fails.

Each function validates a single constraint. If the constraint is violated,
it raises ValueError with a descriptive message. Otherwise it returns silently
(or returns a value for compound checks like validate_order).

These are the building blocks used by validators.py orchestrators.
"""

from fnmatch import fnmatch
from urllib.parse import urlparse
from typing import Literal, Callable, cast

from constants import (
    COMMANDS_MAP,
    TEST_FILE_PATTERNS,
    CODE_EXTENSIONS,
    READ_ONLY_COMMANDS,
    PACKAGE_MANAGER_FILES,
)
from .state_store import StateStore
from .extractors import extract_md_sections
from config import Config


Result = tuple[bool, str]


# ═══════════════════════════════════════════════════════════════════
# Order
# ═══════════════════════════════════════════════════════════════════


def _check_item_in_order(item: str, order: list[str], label: str = "item") -> None:
    if item not in order:
        raise ValueError(f"Invalid {label} '{item}'")


def _check_is_first(next_item: str, order: list[str]) -> None:
    if next_item != order[0]:
        raise ValueError(f"Must start with '{order[0]}', not '{next_item}'")


def _check_not_backwards(prev_item: str, next_item: str, order: list[str]) -> None:
    if order.index(next_item) < order.index(prev_item):
        raise ValueError(f"Cannot go backwards from '{prev_item}' to '{next_item}'")


def _check_no_skip(prev_item: str, next_item: str, order: list[str]) -> None:
    prev_idx = order.index(prev_item)
    next_idx = order.index(next_item)
    if next_idx > prev_idx + 1:
        skipped = order[prev_idx + 1 : next_idx]
        raise ValueError(f"Must complete {skipped} before '{next_item}'")


def validate_order(
    prev_item: str | None, next_item: str, order: list[str]
) -> tuple[bool, str]:
    """Validate transition based on item order."""
    _check_item_in_order(next_item, order, "next item")

    if prev_item is None:
        _check_is_first(next_item, order)
        return True, f"Allowed to start with '{order[0]}'"

    _check_item_in_order(prev_item, order, "previous item")
    _check_not_backwards(prev_item, next_item, order)
    _check_no_skip(prev_item, next_item, order)

    return True, f"Phase is allowed to transition to '{next_item}'"


# ═══════════════════════════════════════════════════════════════════
# Commands (Bash)
# ═══════════════════════════════════════════════════════════════════


def check_read_only(command: str, phase: str) -> Result:
    if any(command.startswith(cmd) for cmd in READ_ONLY_COMMANDS):
        return True, f"Read-only command allowed in phase: {phase}"

    raise ValueError(
        f"Phase '{phase}' only allows read-only commands"
        f"\nAllowed: {READ_ONLY_COMMANDS}"
    )


def check_phase_commands(command: str, phase: str) -> None:
    """Check command against phase-specific whitelist."""
    allowed = COMMANDS_MAP.get(phase, [])
    if allowed and not any(command.startswith(cmd) for cmd in allowed):
        raise ValueError(
            f"Command '{command}' not allowed in phase: {phase}" f"\nAllowed: {allowed}"
        )


def check_pr_create_command(command: str) -> None:
    """Validate gh pr create includes --json for parseable output."""
    if command.startswith("gh pr create") and "--json" not in command:
        raise ValueError(
            f"PR create command must include --json flag" f"\nGot: {command}"
        )


def check_ci_check_command(command: str) -> None:
    """Validate gh pr checks includes --json for parseable output."""
    if command.startswith("gh pr checks") and "--json" not in command:
        raise ValueError(
            f"CI check command must include --json flag" f"\nGot: {command}"
        )


# ═══════════════════════════════════════════════════════════════════
# File Write
# ═══════════════════════════════════════════════════════════════════


def require_agent_completed(agent_name: str, state: StateStore) -> None:
    """Block if the required agent hasn't completed yet."""
    agents = [a for a in state.agents if a.get("name") == agent_name]
    if not agents:
        raise ValueError(f"{agent_name} agent must be invoked first")
    if not all(a.get("status") == "completed" for a in agents):
        raise ValueError(f"{agent_name} agent must complete before writing")


def check_writable_phase(phase: str, config: Config) -> None:
    writable = config.code_write_phases + config.docs_write_phases
    if phase not in writable:
        raise ValueError(f"File write not allowed in phase: {phase}")


def check_plan_path(file_path: str, config: Config) -> None:
    allowed = [config.plan_file_path, config.contracts_file_path]
    if not any(file_path == p or file_path.endswith(p) for p in allowed if p):
        raise ValueError(f"Writing '{file_path}' not allowed" f"\nAllowed: {allowed}")


def _check_has_specifications_section(content: str) -> None:
    if "## Specifications" not in content:
        raise ValueError(
            "Contracts file missing required section: ## Specifications. "
            "See the contracts template for the correct format."
        )


def _check_specifications_has_rows(content: str) -> None:
    from .extractors import extract_table

    sections = extract_md_sections(content, 2)
    for name, body in sections:
        if name.strip() == "Specifications":
            table = extract_table(body)
            if len(table) < 2:  # header + at least 1 data row
                raise ValueError(
                    "## Specifications must have at least one contract in the table. "
                    "See the contracts template for the correct format."
                )
            return

    raise ValueError("## Specifications section is empty.")


def validate_contracts_content(content: str) -> None:
    """Check that contracts file has ## Specifications with at least one table row."""
    _check_has_specifications_section(content)
    _check_specifications_has_rows(content)


def check_test_path(file_path: str) -> None:
    basename = file_path.rsplit("/", 1)[-1]
    if not any(fnmatch(basename, p) for p in TEST_FILE_PATTERNS):
        raise ValueError(
            f"Writing '{file_path}' not allowed"
            f"\nAllowed patterns: {TEST_FILE_PATTERNS}"
        )


def check_code_path(file_path: str) -> None:
    if not any(file_path.endswith(ext) for ext in CODE_EXTENSIONS):
        raise ValueError(
            f"Writing '{file_path}' not allowed"
            f"\nAllowed extensions: {CODE_EXTENSIONS}"
        )


def check_contract_file(file_path: str, contract_files: list[str]) -> None:
    """Define-contracts: only allow files listed in contracts ## Specifications File column."""
    if file_path not in contract_files and not any(
        file_path.endswith(f) for f in contract_files
    ):
        raise ValueError(
            f"Writing '{file_path}' not in contracts ## Specifications file list"
            f"\nAllowed: {contract_files}"
        )


def check_implement_code_path(file_path: str, state: StateStore) -> None:
    """Implement workflow: only allow files listed in plan's Files to Create/Modify."""
    allowed = state.plan_files_to_modify
    if file_path not in allowed:
        raise ValueError(
            f"Writing '{file_path}' not in plan's ## Files to Create/Modify"
            f"\nAllowed: {allowed}"
        )


def validate_build_plan_content(content: str, config: Config) -> None:
    """Check that build plan content contains all required sections with bullet format."""
    required = config.build_plan_required_sections
    missing = [s for s in required if s not in content]
    if missing:
        raise ValueError(f"Plan missing required sections: {missing}")

    sections = extract_md_sections(content, 2)
    section_map = {name.strip(): body for name, body in sections}

    for section_name in config.build_plan_bullet_sections:
        body = section_map.get(section_name, "")
        has_subsections = "### " in body
        has_bullets = any(line.strip().startswith("- ") for line in body.splitlines())

        if has_subsections:
            raise ValueError(
                f"'{section_name}' must use bullet items (- item), not ### subsections. "
                f"See the plan template for the correct format."
            )
        if not has_bullets:
            raise ValueError(
                f"'{section_name}' must have at least one bullet item (- item). "
                f"See the plan template for the correct format."
            )


def validate_implement_plan_content(content: str, config: Config) -> None:
    """Check that implement plan contains: Context, Approach, Files to Create/Modify, Verification."""
    required = config.implement_plan_required_sections
    missing = [s for s in required if s not in content]
    if missing:
        raise ValueError(f"Plan missing required sections: {missing}")


def validate_plan_content(
    content: str, config: Config, workflow_type: str = "build"
) -> None:
    """Dispatch plan validation based on workflow type."""
    if workflow_type == "implement":
        validate_implement_plan_content(content, config)
    else:
        validate_build_plan_content(content, config)


def check_package_manager_path(file_path: str) -> None:
    basename = file_path.rsplit("/", 1)[-1]
    if basename not in PACKAGE_MANAGER_FILES:
        raise ValueError(
            f"Writing '{file_path}' not allowed in install-deps"
            f"\nAllowed: {PACKAGE_MANAGER_FILES}"
        )


def check_report_path(file_path: str, config: Config) -> None:
    expected = config.report_file_path
    if file_path != expected and not file_path.endswith(expected):
        raise ValueError(f"Writing '{file_path}' not allowed" f"\nAllowed: {expected}")


# ═══════════════════════════════════════════════════════════════════
# File Edit
# ═══════════════════════════════════════════════════════════════════


def check_editable_phase(phase: str, config: Config) -> None:
    editable = config.code_edit_phases + config.docs_edit_phases
    if phase not in editable:
        raise ValueError(f"File edit not allowed in phase: {phase}")


def _is_plan_file(file_path: str, config: Config) -> bool:
    plan_path = config.plan_file_path
    return file_path == plan_path or file_path.endswith(plan_path)


def _apply_edit_patch(file_path: str, hook_input: dict) -> str | None:
    """Apply the edit to current content and return patched result, or None if file missing."""
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        return None

    current_content = path.read_text()
    tool_input = hook_input.get("tool_input", {})
    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")
    return current_content.replace(old_string, new_string, 1)


def _check_required_sections_present(content: str, required: list[str]) -> None:
    missing = [s for s in required if s not in content]
    if missing:
        raise ValueError(f"Edit attempted to remove required sections: {missing}")


def validate_plan_edit_preserves_sections(
    hook_input: dict, file_path: str, config: Config, workflow_type: str = "build"
) -> None:
    """Validate that a plan edit doesn't remove required sections."""
    if not _is_plan_file(file_path, config):
        return

    patched = _apply_edit_patch(file_path, hook_input)
    if patched is None:
        return

    required = config.get_plan_required_sections(workflow_type)
    _check_required_sections_present(patched, required)


def check_plan_edit_path(file_path: str, config: Config) -> None:
    expected = config.plan_file_path
    if file_path != expected and not file_path.endswith(expected):
        raise ValueError(f"Editing '{file_path}' not allowed" f"\nAllowed: {expected}")


def check_test_edit_path(file_path: str, state: StateStore) -> None:
    allowed = state.tests.get("file_paths", [])
    if file_path not in allowed:
        raise ValueError(
            f"Editing '{file_path}' not allowed" f"\nTest files in session: {allowed}"
        )


def _check_tests_revised_before_code(state: StateStore) -> None:
    if state.code_tests_to_revise and not state.all_code_tests_revised:
        raise ValueError(
            "Revise test files first before editing code files"
            f"\nTests to revise: {state.code_tests_to_revise}"
            f"\nTests revised: {state.code_tests_revised}"
        )


def _check_file_in_session(file_path: str, allowed: list[str], label: str) -> None:
    if file_path not in allowed:
        raise ValueError(
            f"Editing '{file_path}' not allowed" f"\n{label} in session: {allowed}"
        )


def check_code_edit_path(file_path: str, state: StateStore) -> None:
    test_files = state.tests.get("file_paths", [])
    code_files = state.code_files.get("file_paths", [])

    if file_path in test_files:
        return

    if file_path in code_files:
        _check_tests_revised_before_code(state)
        return

    _check_file_in_session(file_path, code_files, "Code files")


# ═══════════════════════════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════════════════════════


def check_expected_agent(next_agent: str, phase: str, config: Config) -> None:
    expected = config.get_required_agent(phase)
    if not expected:
        raise ValueError(f"No agent allowed in phase: {phase}")
    if next_agent != expected:
        raise ValueError(
            f"Agent '{next_agent}' not allowed in phase: {phase}"
            f"\nExpected: {expected}"
        )


def check_agent_count(
    next_agent: str, phase: str, config: Config, state: StateStore
) -> None:
    max_allowed = config.get_agent_max_count(next_agent)
    actual = state.count_agents(next_agent)
    if actual >= max_allowed:
        raise ValueError(
            f"Agent '{next_agent}' at max ({max_allowed}) in phase: {phase}"
        )


def _check_plan_revision_done(state: StateStore) -> None:
    if state.plan_revised is False:
        raise ValueError("Plan must be revised before re-invoking PlanReview")


def _check_test_revision_done(state: StateStore) -> None:
    last = state.last_test_review
    if last and last.get("verdict") == "Fail":
        if not state.all_test_files_revised:
            raise ValueError(
                "All test files must be revised before re-invoking TestReviewer"
                f"\nFiles to revise: {state.test_files_to_revise}"
                f"\nFiles revised: {state.test_files_revised}"
            )


def _check_code_revision_done(state: StateStore) -> None:
    last = state.last_code_review
    if last and last.get("status") == "Fail":
        if not state.all_files_revised:
            raise ValueError(
                "All files must be revised before re-invoking CodeReviewer"
                f"\nFiles to revise: {state.files_to_revise}"
                f"\nFiles revised: {state.files_revised}"
            )


def check_revision_done(next_agent: str, phase: str, state: StateStore) -> None:
    """Block review agents if revision hasn't happened since last Fail."""
    if phase == "plan-review" and next_agent == "PlanReview":
        _check_plan_revision_done(state)
    if phase in ("test-review", "tests-review") and next_agent == "TestReviewer":
        _check_test_revision_done(state)
    if phase == "code-review" and next_agent == "CodeReviewer":
        _check_code_revision_done(state)


# ═══════════════════════════════════════════════════════════════════
# URL
# ═══════════════════════════════════════════════════════════════════


def check_safe_domain(url: str, config: Config) -> Result:
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


# ═══════════════════════════════════════════════════════════════════
# Score / verdict
# ═══════════════════════════════════════════════════════════════════


def check_score_present(confidence: int | None, quality: int | None) -> None:
    if confidence is None or quality is None:
        raise ValueError("Confidence and quality scores are required")


def check_score_range(confidence: int, quality: int) -> None:
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

    check_score_present(confidence, quality)
    check_score_range(confidence, quality)  # type: ignore[arg-type]

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


SCORE_PHASES = ["plan-review", "code-review"]
VERDICT_PHASES = ["test-review", "tests-review", "quality-check", "validate"]


def _check_report_not_empty(content: str) -> None:
    if not content:
        raise ValueError("Agent report is empty")


def _check_phase_requires_report(phase: str) -> None:
    if phase not in SCORE_PHASES and phase not in VERDICT_PHASES:
        raise ValueError(f"Phase '{phase}' does not require an agent report")


def is_agent_report_valid(
    hook_input: dict,
    state: StateStore,
    score_extractor: Callable[
        [str], dict[Literal["confidence_score", "quality_score"], int | None]
    ],
    verdict_extractor: Callable[[str], str],
) -> Result:
    """Validate the agent's report based on current phase."""
    phase = state.current_phase
    content = hook_input.get("last_assistant_message", "")

    _check_report_not_empty(content)
    _check_phase_requires_report(phase)

    if phase in SCORE_PHASES:
        scores_valid(content, score_extractor)
        return True, f"Agent report valid for {phase}: scores present"

    verdict_valid(content, verdict_extractor)
    return True, f"Agent report valid for {phase}: verdict present"


# ═══════════════════════════════════════════════════════════════════
# Review sections
# ═══════════════════════════════════════════════════════════════════


def _extract_bullet_items(content: str) -> list[str]:
    """Extract bullet list items (- item) from markdown content."""
    return [
        line.lstrip("- ").strip()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    ]


def _require_section(sections: dict[str, str], heading: str) -> list[str]:
    """Require a section exists and has bullet items. Returns the items."""
    if heading not in sections:
        raise ValueError(f"'{heading}' section is required")
    items = _extract_bullet_items(sections[heading])
    if not items:
        raise ValueError(f"'{heading}' section is empty — provide file paths")
    return items


def validate_review_sections(content: str, phase: str) -> tuple[list[str], list[str]]:
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

    if phase in ("test-review", "tests-review"):
        files = _require_section(sections, "Files to revise")
        return files, []

    return [], []
