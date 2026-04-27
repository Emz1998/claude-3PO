"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from typing import Literal
from utils.hook import Hook  # type: ignore
from config import Config  # type: ignore
from pathlib import Path  # type: ignore

Decision = tuple[Literal["allow", "block"], str]
DEFAULT_STATE_PATH = Path.cwd() / "claude-3PO" / "state.json"


def get_safe_domains() -> list[str]:
    config = Config()
    return config.safe_domains


def validate_domain(domain: str, safe_domains: list[str]) -> tuple[bool, str]:
    if domain in safe_domains:
        return True, "Domain is safe"
    return False, "Domain is not safe"


def main() -> None:
    hook_input = Hook.read_stdin()
    domain = hook_input.get("tool_input", {}).get("url", "")
    safe_domains = get_safe_domains()

    errors: list[str] = []
    is_safe, error = validate_domain(domain, safe_domains)
    if not is_safe:
        errors.append(error)
    if errors:
        Hook.block("\n".join(errors))
        return


if __name__ == "__main__":
    main()
