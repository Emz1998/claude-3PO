"""plan_guardrail.py — Plan workflow guardrail CLI hook.

Enforces the /plan skill workflow:
  1. Skill interception: /plan triggers explore phase (Explore x3 + Research x2)
  2. Plan agent runs after explore is complete
  3. Main agent writes plan file to .claude/plans/
  4. Plan-Review agent reviews the written plan (confidence/quality >= 80, max 3 iterations)
  5. ExitPlanMode validates plan against template

Usage:
    python3 plan_guardrail.py --hook-input '{"hook_event_name":"PreToolUse",...}'
    python3 plan_guardrail.py --hook-input '...' --reason

Environment:
    PLAN_GUARDRAIL_STATE_PATH — override the default state.json path
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workflow.guards.agent_guard import (
    count as _count,
    count_completed as _count_completed,
)
from workflow.guards.review_guard import parse_scores as _parse_review_scores
from workflow.state_store import StateStore

DEFAULT_STATE_PATH = Path(__file__).resolve().parent / "state.json"

SAFE_DOMAINS = [
    "docs.python.org",
    "docs.anthropic.com",
    "developer.mozilla.org",
    "reactjs.org",
    "react.dev",
    "nextjs.org",
    "tailwindcss.com",
    "github.com",
    "stackoverflow.com",
    "pypi.org",
    "npmjs.com",
    "typescriptlang.org",
    "nodejs.org",
    "firebase.google.com",
    "supabase.com",
    "expo.dev",
    "reactnative.dev",
]

REQUIRED_SECTIONS = [
    r"^##\s+Context",
    r"^##\s+(Approach|Steps)",
    r"^##\s+(Files to Modify|Critical Files)",
    r"^##\s+Verification",
]

# Agent limits
EXPLORE_MAX = 3
RESEARCH_MAX = 2
PLAN_MAX = 1
PLAN_REVIEW_MAX = 3


def _state_path() -> Path:
    env = os.environ.get("PLAN_GUARDRAIL_STATE_PATH")
    return Path(env) if env else DEFAULT_STATE_PATH


def _parse_skip_args(args: str) -> dict:
    return {
        "skip_explore": "--skip-explore" in args or "--skip-all" in args,
        "skip_research": "--skip-research" in args or "--skip-all" in args,
    }


def _parse_instructions(args: str) -> str:
    """Extract free-form instructions from args after stripping known flags."""
    flags = ["--skip-explore", "--skip-research", "--skip-all"]
    text = args
    for flag in flags:
        text = text.replace(flag, "")
    return text.strip()


def _required_agents(skip: dict) -> dict[str, int]:
    required = {}
    if not skip.get("skip_explore"):
        required["Explore"] = EXPLORE_MAX
    if not skip.get("skip_research"):
        required["Research"] = RESEARCH_MAX
    return required


def _default_plan_workflow(skip: dict | None = None, instructions: str = "") -> dict:
    return {
        "plan_workflow_active": True,
        "phase": "explore",
        "skip": skip or {"skip_explore": False, "skip_research": False},
        "instructions": instructions,
        "agents": [],
        "plan_file": None,
        "plan_written": False,
        "review": {
            "iteration": 0,
            "max_iterations": 3,
            "threshold": {"confidence": 80, "quality": 80},
            "scores": None,
            "status": None,
        },
    }


def _validate_plan_template(content: str) -> tuple[bool, list[str]]:
    """Check plan content has all required sections. Returns (passed, missing)."""
    missing = []
    for pattern in REQUIRED_SECTIONS:
        if not re.search(pattern, content, re.MULTILINE):
            # Human-readable label
            label = re.sub(r"\^##\\s\+", "", pattern)
            label = (
                label.replace("(", "")
                .replace(")", "")
                .replace("|", " or ")
                .replace("\\", "")
            )
            missing.append(label.strip())
    return len(missing) == 0, missing


def _is_safe_domain(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not host:
            return False
        for domain in SAFE_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


def _is_plan_file_path(file_path: str) -> bool:
    plans_dir = ".claude/plans/"
    return file_path.startswith(plans_dir) or f"/{plans_dir}" in file_path


def _get_write_file_path(hook_input: dict) -> str:
    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})
    return tool_input.get("file_path", "") or tool_response.get("filePath", "")


def get_skill_and_args(hook_input: dict) -> tuple[str, str]:
    hook_event_name = hook_input.get("hook_event_name", "")
    match hook_event_name:
        case "UserPromptSubmit":
            prompt = hook_input.get("prompt", "")
            parsed = prompt.split(" ", 1)
            return parsed[0].replace("/", ""), parsed[1] if len(parsed) > 1 else ""
        case "PostToolUse":
            tool_input = hook_input.get("tool_input", {})
            skill = tool_input.get("skill", "")
            args = tool_input.get("args", "")
            return skill, args
        case _:
            return "", ""


def _handle_skill(hook_input: dict, store: StateStore) -> tuple[str, str]:
    skill, args = get_skill_and_args(hook_input)
    if skill != "plan":
        return "allow", ""

    skip = _parse_skip_args(args)
    instructions = _parse_instructions(args)
    workflow = _default_plan_workflow(skip, instructions)

    # If skip-all or both skips, go straight to plan phase
    if skip.get("skip_explore") and skip.get("skip_research"):
        workflow["phase"] = "plan"

    def _activate(state: dict) -> None:
        state["workflow_active"] = True
        state["workflow_type"] = "plan"
        state["plan_workflow"] = workflow

    store.update(_activate)
    return "allow", ""


def _handle_agent(hook_input: dict, store: StateStore) -> tuple[str, str]:
    tool_input = hook_input.get("tool_input", {})
    agent_type = tool_input.get("subagent_type", "")
    tool_use_id = hook_input.get("tool_use_id", "")

    state = store.load()
    pw = state.get("plan_workflow")
    if not pw or not pw.get("plan_workflow_active"):
        return "allow", ""

    phase = pw.get("phase", "")
    agents = pw.get("agents", [])
    skip = pw.get("skip", {})

    # Block background execution for Explore and Research agents
    if agent_type in ("Explore", "Research") and tool_input.get("run_in_background"):
        return (
            "block",
            f"Agent '{agent_type}' must not run in background — set run_in_background to false",
        )

    # Explore agents — only in explore phase
    if agent_type == "Explore":
        if phase != "explore":
            return "block", f"Agent 'Explore' not allowed in phase '{phase}'"
        if skip.get("skip_explore"):
            return "block", "Explore agents skipped (--skip-explore)"
        current = _count(agents, "Explore")
        if current >= EXPLORE_MAX:
            return "block", f"Max agents ({EXPLORE_MAX}) for 'Explore' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # Research agents — only in explore phase
    if agent_type == "Research":
        if phase != "explore":
            return "block", f"Agent 'Research' not allowed in phase '{phase}'"
        if skip.get("skip_research"):
            return "block", "Research agents skipped (--skip-research)"
        current = _count(agents, "Research")
        if current >= RESEARCH_MAX:
            return "block", f"Max agents ({RESEARCH_MAX}) for 'Research' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # Plan agent — only in plan phase, after required agents complete
    if agent_type == "Plan":
        if phase != "plan":
            # Check if we're still in explore but required agents done
            if phase == "explore":
                required = _required_agents(skip)
                all_done = all(
                    _count_completed(agents, atype) >= count
                    for atype, count in required.items()
                )
                if not all_done:
                    return (
                        "block",
                        "Plan agent requires all explore/research agents to complete first",
                    )
            else:
                return "block", f"Plan agent not allowed in phase '{phase}'"
        current = _count(agents, "Plan")
        if current >= PLAN_MAX:
            return "block", f"Max agents ({PLAN_MAX}) for 'Plan' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    # Plan-Review agent — only in review phase
    if agent_type == "Plan-Review":
        if phase != "review":
            return (
                "block",
                f"Plan-Review agent not allowed in phase '{phase}'. Must be in review phase.",
            )
        if not pw.get("plan_written") or not pw.get("plan_file"):
            return (
                "block",
                "Plan-Review requires a successful Write to .claude/plans/ first",
            )
        current = _count(agents, "Plan-Review")
        if current >= PLAN_REVIEW_MAX:
            return "block", f"Max agents ({PLAN_REVIEW_MAX}) for 'Plan-Review' reached"
        _record_agent(store, agent_type, tool_use_id)
        return "allow", ""

    allowed = ["Explore", "Research", "Plan", "Plan-Review"]
    return (
        "block",
        f"Agent '{agent_type}' not allowed in plan workflow. Allowed: {', '.join(allowed)}",
    )


def _record_agent(store: StateStore, agent_type: str, tool_use_id: str) -> None:
    def _update(state: dict) -> None:
        pw = state.get("plan_workflow", {})
        pw.setdefault("agents", []).append(
            {
                "agent_type": agent_type,
                "status": "running",
                "tool_use_id": tool_use_id,
            }
        )
        state["plan_workflow"] = pw

    store.update(_update)


def _handle_webfetch(hook_input: dict) -> tuple[str, str]:
    url = hook_input.get("tool_input", {}).get("url", "")
    if not _is_safe_domain(url):
        return (
            "block",
            f"Domain not allowed. URL must be from approved domains: {', '.join(SAFE_DOMAINS[:5])}...",
        )
    return "allow", ""


def _handle_write(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    pw = state.get("plan_workflow")
    if not pw or not pw.get("plan_workflow_active"):
        return "allow", ""

    file_path = _get_write_file_path(hook_input)
    if not _is_plan_file_path(file_path):
        return (
            "block",
            f"Plan files must be written to .claude/plans/ directory. Got: '{file_path}'",
        )
    return "allow", ""


def _handle_write_post(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    pw = state.get("plan_workflow")
    if not pw or not pw.get("plan_workflow_active"):
        return "allow", ""

    file_path = _get_write_file_path(hook_input)
    if not _is_plan_file_path(file_path):
        return "allow", ""

    phase = pw.get("phase")
    if phase not in {"write", "review"}:
        return "allow", ""

    def _record_written_plan(s: dict) -> None:
        workflow = s.get("plan_workflow", {})
        workflow["plan_file"] = file_path
        workflow["plan_written"] = True
        workflow["phase"] = "review"
        s["plan_workflow"] = workflow

    store.update(_record_written_plan)
    return "allow", ""


def _handle_exit_plan_mode(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    pw = state.get("plan_workflow")
    if not pw or not pw.get("plan_workflow_active"):
        return "allow", ""

    if not pw.get("plan_written"):
        return (
            "block",
            "No written plan recorded. Write the plan to .claude/plans/ first.",
        )

    review = pw.get("review", {})
    if review.get("status") != "approved":
        return (
            "block",
            "Plan review is not approved yet. Run Plan-Review after writing the plan.",
        )

    plan_file = pw.get("plan_file")
    if not plan_file:
        return "block", "No plan file recorded. Write the plan to .claude/plans/ first."

    try:
        content = Path(plan_file).read_text()
    except (FileNotFoundError, OSError) as e:
        return "block", f"Cannot read plan file '{plan_file}': {e}"

    passed, missing = _validate_plan_template(content)
    if not passed:
        return "block", f"Plan missing required sections: {', '.join(missing)}"

    return json.dumps({"additionalContext": f"Plan content:\n\n{content}"}), ""


def _handle_subagent_stop(hook_input: dict, store: StateStore) -> tuple[str, str]:
    agent_type = hook_input.get("agent_type", "")
    last_message = hook_input.get("last_assistant_message", "")

    def _process(state: dict) -> None:
        pw = state.get("plan_workflow")
        if not pw or not pw.get("plan_workflow_active"):
            return

        agents = pw.get("agents", [])

        # Mark first matching running agent as completed
        for a in agents:
            if a.get("agent_type") == agent_type and a.get("status") == "running":
                a["status"] = "completed"
                break

        phase = pw.get("phase", "")
        skip = pw.get("skip", {})

        if agent_type in ("Explore", "Research"):
            required = _required_agents(skip)
            all_done = all(
                _count_completed(agents, atype) >= count
                for atype, count in required.items()
            )
            if all_done:
                pw["phase"] = "plan"

        elif agent_type == "Plan":
            pw["phase"] = "write"

        elif agent_type == "Plan-Review":
            review = pw.get("review", {})
            scores = _parse_review_scores(last_message)
            review["scores"] = scores

            threshold = review.get("threshold", {"confidence": 80, "quality": 80})
            iteration = review.get("iteration", 0)
            max_iter = review.get("max_iterations", 3)

            passed = (
                scores["confidence"] is not None
                and scores["quality"] is not None
                and scores["confidence"] >= threshold["confidence"]
                and scores["quality"] >= threshold["quality"]
            )

            if passed:
                review["status"] = "approved"
                pw["phase"] = "approved"
            elif iteration + 1 >= max_iter:
                review["status"] = "max_iterations_reached"
                review["iteration"] = iteration + 1
                pw["phase"] = "failed"
            else:
                review["status"] = "revision_needed"
                review["iteration"] = iteration + 1

            pw["review"] = review

        state["plan_workflow"] = pw

    store.update(_process)
    return "allow", ""


def _dispatch(hook_input: dict, state_path: Path) -> tuple[str, str]:
    store = StateStore(state_path)
    event = hook_input.get("hook_event_name", "")
    tool = hook_input.get("tool_name", "")

    if event == "PreToolUse":
        if tool == "Agent":
            return _handle_agent(hook_input, store)
        if tool == "WebFetch":
            state = store.load()
            if state.get("workflow_active"):
                return _handle_webfetch(hook_input)
            return "allow", ""
        if tool == "Write":
            return _handle_write(hook_input, store)
        if tool == "ExitPlanMode":
            return _handle_exit_plan_mode(hook_input, store)

    if event == "PostToolUse":
        if tool == "Skill":
            return _handle_skill(hook_input, store)
        if tool == "Write":
            return _handle_write_post(hook_input, store)

    if event == "SubagentStop":
        return _handle_subagent_stop(hook_input, store)

    if event == "UserPromptSubmit":
        return _handle_skill(hook_input, store)

    return "allow", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan workflow guardrail hook")
    parser.add_argument("--hook-input", type=str, help="JSON hook input string")
    parser.add_argument(
        "--reason", action="store_true", help="Include block reason in output"
    )
    args = parser.parse_args()

    if not args.hook_input:
        parser.print_help()
        sys.exit(1)

    try:
        hook_input = json.loads(args.hook_input)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    state_path = _state_path()
    decision, reason = _dispatch(hook_input, state_path)

    if decision == "allow":
        print("allow")
    elif decision == "block":
        print(f"block, {reason}" if args.reason else "block")
    else:
        # JSON passthrough (WebSearch updatedInput, ExitPlanMode additionalContext)
        print(decision)

    sys.exit(0)


if __name__ == "__main__":
    main()
