#!/usr/bin/env python3
"""Tracker for validating and recording release plan logging commands.

Validates log:task, log:ac, and log:sc skill arguments against the release plan
and records state changes after successful execution.
"""

import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils import read_stdin_json  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.state_manager import get_manager  # type: ignore
from release_plan.utils import (  # type: ignore
    find_task,
    find_acceptance_criteria,
    find_success_criteria,
)
from release_plan.resolvers import (  # type: ignore
    record_completed_task,
    record_met_ac,
    record_met_sc,
)
from release_plan.checkers import (  # type: ignore
    are_all_tasks_completed_in_user_story,
    are_all_user_stories_completed_in_feature,
    are_all_features_completed_in_epic,
    is_ac_met,
    is_sc_met,
)
from release_plan.getters import (  # type: ignore
    get_current_user_story,
    get_current_feature_id,
    get_current_epic_id,
)
from release_plan.utils import (  # type: ignore
    get_all_acs_ids_in_user_story,
    get_all_scs_ids_in_feature,
    find_epic,
    load_release_plan,
    get_release_plan_path,
)

RELEASE_PLAN_PATH = get_release_plan_path("v0.1.0")

# Valid statuses for each type
TASK_STATUSES = ["not_started", "in_progress", "completed", "blocked"]
AC_STATUSES = ["met", "unmet"]
SC_STATUSES = ["met", "unmet"]


class ReleasePlanTracker:
    """Tracker for validating and recording release plan logging commands."""

    def __init__(self):
        """Initialize the tracker."""
        self._state = get_manager()

    def is_active(self) -> bool:
        """Check if tracker is active (workflow is active)."""
        return self._state.is_workflow_active()

    def _parse_skill_args(self, args: str) -> Tuple[str, str]:
        """Parse skill arguments into ID and status.

        Args:
            args: Space-separated skill arguments (e.g., "T001 completed")

        Returns:
            Tuple of (item_id, status)
        """
        if not args:
            return "", ""
        parts = args.split()
        if len(parts) < 2:
            return parts[0] if parts else "", ""
        return parts[0], parts[1]

    def _is_revision_task_id(self, task_id: str) -> bool:
        """Check if task ID is a revision task (RT-prefixed)."""
        return task_id.startswith("RT-")

    def validate_log_task(self, args: str) -> Tuple[bool, str]:
        """Validate log:task skill arguments.

        Args:
            args: Skill arguments (e.g., "T001 completed" or "RT-1-001 completed")

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not args:
            return False, "Missing log:task arguments. Expected: TXXX status"

        task_id, status = self._parse_skill_args(args)

        if not task_id:
            return False, "Missing task ID. Expected: TXXX status"

        if not status:
            return (
                False,
                f"Missing status. Expected: {task_id} {' | '.join(TASK_STATUSES)}",
            )

        if status not in TASK_STATUSES:
            return (
                False,
                f"Invalid status '{status}'. Expected: {' | '.join(TASK_STATUSES)}",
            )

        # RT- prefixed IDs are revision tasks, validate against current_tasks
        if self._is_revision_task_id(task_id):
            from release_plan.state import load_project_state  # type: ignore

            project_state = load_project_state() or {}
            current_tasks = project_state.get("current_tasks", {})
            if task_id not in current_tasks:
                return False, f"Revision task '{task_id}' not found in current tasks"
            return True, ""

        task = find_task(task_id)
        if task is None:
            return False, f"Task '{task_id}' not found in release plan"

        return True, ""

    def validate_log_ac(self, args: str) -> Tuple[bool, str]:
        """Validate log:ac skill arguments.

        Args:
            args: Skill arguments (e.g., "AC-001 met")

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not args:
            return False, "Missing log:ac arguments. Expected: AC-XXX status"

        ac_id, status = self._parse_skill_args(args)

        if not ac_id:
            return False, "Missing AC ID. Expected: AC-XXX status"

        if not status:
            return (
                False,
                f"Missing status. Expected: {ac_id} {' | '.join(AC_STATUSES)}",
            )

        if status not in AC_STATUSES:
            return (
                False,
                f"Invalid status '{status}'. Expected: {' | '.join(AC_STATUSES)}",
            )

        ac = find_acceptance_criteria(ac_id)
        if ac is None:
            return False, f"Acceptance criteria '{ac_id}' not found in release plan"

        return True, ""

    def validate_log_sc(self, args: str) -> Tuple[bool, str]:
        """Validate log:sc skill arguments.

        Args:
            args: Skill arguments (e.g., "SC-001 met")

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not args:
            return False, "Missing log:sc arguments. Expected: SC-XXX status"

        sc_id, status = self._parse_skill_args(args)

        if not sc_id:
            return False, "Missing SC ID. Expected: SC-XXX status"

        if not status:
            return (
                False,
                f"Missing status. Expected: {sc_id} {' | '.join(SC_STATUSES)}",
            )

        if status not in SC_STATUSES:
            return (
                False,
                f"Invalid status '{status}'. Expected: {' | '.join(SC_STATUSES)}",
            )

        sc = find_success_criteria(sc_id)
        if sc is None:
            return False, f"Success criteria '{sc_id}' not found in release plan"

        return True, ""

    def run_pre_tool(self, hook_input: dict) -> None:
        """Run pre-tool validation.

        Validates that the skill arguments reference valid IDs in the release plan.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            return

        tool_name = hook_input.get("tool_name", "")
        if tool_name != "Skill":
            return

        skill_name = hook_input.get("tool_input", {}).get("skill", "")
        skill_args = hook_input.get("tool_input", {}).get("args", "")

        validators = {
            "log:task": self.validate_log_task,
            "log:ac": self.validate_log_ac,
            "log:sc": self.validate_log_sc,
        }

        validator = validators.get(skill_name)
        if validator is None:
            return

        is_valid, reason = validator(skill_args)
        if not is_valid:
            print(reason, file=sys.stderr)
            sys.exit(2)

    def run_post_tool(self, hook_input: dict) -> None:
        """Run post-tool recording.

        Records completed items in the project state after successful skill execution.

        Args:
            hook_input: The hook input dictionary
        """
        if not self.is_active():
            return

        tool_name = hook_input.get("tool_name", "")
        if tool_name != "Skill":
            return

        skill_name = hook_input.get("tool_input", {}).get("skill", "")
        skill_args = hook_input.get("tool_input", {}).get("args", "")

        item_id, status = self._parse_skill_args(skill_args)
        if not item_id or not status:
            return

        if skill_name == "log:task" and status == "completed":
            record_completed_task(item_id)
            self._check_ac_validation_needed()
        elif skill_name == "log:ac" and status == "met":
            record_met_ac(item_id)
            self._check_sc_validation_needed()
        elif skill_name == "log:sc" and status == "met":
            record_met_sc(item_id)
            self._check_epic_sc_validation_needed()

    def _check_ac_validation_needed(self) -> None:
        """After task completion, check if AC validation is needed."""
        from release_plan.state import load_project_state  # type: ignore

        project_state = load_project_state() or {}
        current_us = get_current_user_story(project_state)
        if not current_us:
            return

        if not are_all_tasks_completed_in_user_story(current_us, project_state):
            return

        release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
        all_ac_ids = get_all_acs_ids_in_user_story(current_us, release_plan) or []
        unmet = [ac for ac in all_ac_ids if not is_ac_met(ac, project_state)]
        if unmet:
            self._state.set("needs_ac_validation", True)

    def _check_sc_validation_needed(self) -> None:
        """After AC met, check if SC validation is needed."""
        from release_plan.state import load_project_state  # type: ignore

        project_state = load_project_state() or {}
        current_feature = get_current_feature_id(project_state)
        if not current_feature:
            return

        if not are_all_user_stories_completed_in_feature(
            current_feature, project_state
        ):
            return

        release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
        all_sc_ids = get_all_scs_ids_in_feature(current_feature, release_plan) or []
        unmet = [sc for sc in all_sc_ids if not is_sc_met(sc, project_state)]
        if unmet:
            self._state.set("needs_sc_validation", True)

    def _check_epic_sc_validation_needed(self) -> None:
        """After SC met, check if epic SC validation is needed."""
        from release_plan.state import load_project_state  # type: ignore

        project_state = load_project_state() or {}
        current_epic = get_current_epic_id(project_state)
        if not current_epic:
            return

        if not are_all_features_completed_in_epic(current_epic, project_state):
            return

        release_plan = load_release_plan(RELEASE_PLAN_PATH) or {}
        epic = find_epic(current_epic, release_plan) or {}
        epic_scs = epic.get("success_criteria", [])
        met_epic_scs = project_state.get("met_epic_scs", [])
        unmet = [sc for sc in epic_scs if sc.get("id", "") not in met_epic_scs]
        if unmet:
            self._state.set("needs_epic_sc_validation", True)

    def run(self, hook_input: dict) -> None:
        """Run the tracker (backwards compatible with old interface).

        Args:
            hook_input: The hook input dictionary
        """
        hook_event_name = hook_input.get("hook_event_name", "")

        if hook_event_name == "PreToolUse":
            self.run_pre_tool(hook_input)
        elif hook_event_name == "PostToolUse":
            self.run_post_tool(hook_input)


def track_release_plan(hook_input: dict) -> None:
    """Track release plan logging commands.

    Args:
        hook_input: The hook input dictionary
    """
    tracker = ReleasePlanTracker()
    tracker.run(hook_input)


def main() -> None:
    """Main entry point for the tracker."""
    hook_input = read_stdin_json()
    if not hook_input:
        sys.exit(0)

    tracker = ReleasePlanTracker()
    tracker.run(hook_input)


if __name__ == "__main__":
    main()
