import sys
import subprocess
import json
from typing import Literal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from lib.subprocess_agents import invoke_headless_agent  # type: ignore
from lib.validators import template_conformance_check  # type: ignore


TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "pr.md"


def create_pr(
    title: str, body: str, base: str | None = None, head: str | None = None
) -> str:
    cmd = ["gh", "pr", "create", "--title", title, "--body", body]
    if base:
        cmd += ["--base", base]
    if head:
        cmd += ["--head", head]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def ask_pr_title(
    prompt: str | None = None, body: str | None = None, session_id: str | None = None
) -> str:
    if prompt is None:
        prompt = f"Generate a title for the pull request title for this pr body {body}"
    raw_output = invoke_headless_agent(
        "claude", prompt, 60, model="haiku", output_format="json", session_id=session_id
    )
    if not raw_output:
        return ""

    output = json.loads(raw_output)

    response = output.get("result", "")

    session_id = output.get("session_id", "")
    print(session_id)
    if not session_id:
        return ""

    if not response or response is None:
        ask_pr_title(prompt, body, session_id)
    return response


def get_pr_body(hook_input: dict) -> str:
    hook_event_name = hook_input.get("hook_event_name")
    if hook_event_name != "Stop":
        return ""
    report = hook_input.get("last_assistant_message", "")
    return report


def handle_pr_creation(hook_input: dict) -> tuple[Literal["allow", "block"], str]:
    pr_body = get_pr_body(hook_input)
    if not pr_body:
        return ("block", "No PR body found")
    pr_title = ask_pr_title(pr_body)
    if not pr_title:
        return ("block", "No PR title found")
    ok, diff = template_conformance_check(pr_body, TEMPLATE_PATH)
    if not ok:
        return ("block", diff)

    title = ask_pr_title(pr_body)

    create_pr_url = create_pr(title, pr_body)
    if not create_pr_url:
        return ("block", "Failed to create PR")
    return ("allow", "PR creation successful")
