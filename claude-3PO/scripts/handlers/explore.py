"""Research handler — thin handler that delegates to lib.reviewer.

Runs the research phase of the workflow.
"""

from pathlib import Path
from typing_extensions import Literal

from config import Config  # type: ignore
from lib.validators import template_conformance_check  # type: ignore
from handlers.guardrails.webfetch_guard import WebFetchGuard  # type: ignore
from handlers.guardrails.webfetch_guard import Decision  # type: ignore
from lib.state_store import StateStore  # type: ignore

DEFAULT_REPORT_TEMPLATE = (
    Path(__file__).parent.parent.parent / "templates" / "research.md"
)


class Explore:
    def __init__(self, hook_input: dict, state: StateStore, config: Config):
        self.hook_input = hook_input
        self.config = config
        self.state = state
        self.phase = self.state.get("phase", "explore")

    @property
    def last_assistant_message(self) -> str:
        return self.hook_input.get("last_assistant_message", "")

    def setup_webfetch_guard(self) -> Decision:
        guard = WebFetchGuard(self.hook_input, self.config)
        return guard.validate()

    def run_guardrails(
        self, guard_type: Literal["webfetch", "template_check"]
    ) -> Decision:
        if not self.phase == "research":
            return "allow", "Not in research phase"
        if guard_type == "webfetch":
            return self.setup_webfetch_guard()
        if guard_type == "template_check":
            return self.validate_research_report()
