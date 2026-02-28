#!/usr/bin/env python3
"""Dry run test for Claude Code hook dispatchers.

Simulates a realistic hook workflow by piping JSON input to dispatchers
via subprocess, matching how Claude Code invokes hooks at runtime.
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json
import re
from typing import Any

import shutil

from scripts.claude_hooks.utils.file_manager import FileManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPRINTS_DIR = PROJECT_ROOT / "project" / "sprints"
HISTORY_PATH = SPRINTS_DIR / "history.jsonl"
DEFAULT_SPRINT = "SPRINT-001"


# Dispatcher script paths
DISPATCHERS: dict[str, Path] = {
    "PreToolUse": Path(".claude/hooks/dispatchers/pre_tool.py"),
    "PostToolUse": Path(".claude/hooks/dispatchers/post_tool.py"),
    "Stop": Path(".claude/hooks/dispatchers/stop.py"),
    "UserPromptSubmit": Path(".claude/hooks/dispatchers/user_prompt.py"),
}

# Hook events that require tool_name
TOOL_EVENTS = {"PreToolUse", "PostToolUse"}

ALL_EVENTS = {
    *TOOL_EVENTS,
    "PostToolUseFailure",
    "PermissionRequest",
    "UserPromptSubmit",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "SessionEnd",
    "SessionStart",
    "Stop",
}


def camel_to_underscore(name: str) -> str:
    parts = re.findall(r"[A-Z][a-z]*", name)
    return "_".join(parts).lower()


def resolve_schema_path(hook_event: str, tool_name: str | None = None) -> Path:
    """Resolve the input schema JSON path for a hook event."""
    if hook_event not in ALL_EVENTS:
        raise ValueError(f"Invalid hook event: {hook_event}")
    if hook_event in TOOL_EVENTS and tool_name is None:
        raise ValueError(f"tool_name required for {hook_event}")

    base = Path.cwd() / "input-schemas"
    if hook_event in TOOL_EVENTS:
        subdir = camel_to_underscore(hook_event)
        return base / subdir / f"{tool_name}.json".lower()

    return base / f"{camel_to_underscore(hook_event)}.json"


class SchemaLoader:
    """Loads and patches hook input JSON from schema files."""

    def __init__(self, hook_event: str, tool_name: str | None = None):
        path = resolve_schema_path(hook_event, tool_name)
        self._file = FileManager(path)
        self._data: dict[str, Any] = dict(self._file.load() or {})

    def patch(self, overrides: dict[str, Any]) -> None:
        self._data.update(overrides)
        self._file.save(self._data)

    def to_json(self) -> str:
        return json.dumps(self._data)

    @property
    def data(self) -> dict[str, Any]:
        return self._data


def run_dispatcher(hook_event: str, input_json: str) -> subprocess.CompletedProcess:
    """Run a dispatcher script with JSON piped to stdin."""
    script = DISPATCHERS.get(hook_event)
    if script is None:
        raise ValueError(f"No dispatcher for {hook_event}")
    return subprocess.run(
        [sys.executable, str(script)],
        input=input_json,
        text=True,
        capture_output=True,
    )


# Step definitions
@dataclass
class Step:
    hook_event: str
    timeout: int = 0


@dataclass
class ToolStep(Step):
    hook_event: str = "PreToolUse"
    tool_name: str = "Skill"
    tool_input: dict[str, Any] | None = None
    post: bool = True


@dataclass
class UserPromptStep(Step):
    prompt: str = ""


@dataclass
class StopStep(Step):
    pass


class DryRun:
    """Runs a sequence of hook steps against dispatchers."""

    def __init__(self, session_id: str, steps: list[Step]):
        self._session_id = session_id
        self._steps = list(steps)

    def _run_tool_step(self, step: ToolStep) -> bool:
        # PreToolUse
        loader = SchemaLoader("PreToolUse", step.tool_name)
        loader.patch(
            {
                "session_id": self._session_id,
                "tool_input": step.tool_input or {},
            }
        )
        result = run_dispatcher("PreToolUse", loader.to_json())
        self._print_result(step, result)

        if result.returncode != 0:
            return False

        if step.timeout > 0:
            print(f"  [simulating {step.timeout}s work...]", flush=True)
            time.sleep(step.timeout)

        # PostToolUse (auto-fires on PreToolUse success)
        if step.post:
            post_loader = SchemaLoader("PostToolUse", step.tool_name)
            post_loader.patch(
                {
                    "session_id": self._session_id,
                    "tool_input": step.tool_input or {},
                }
            )
            post_result = run_dispatcher("PostToolUse", post_loader.to_json())
            step.hook_event = "PostToolUse"
            self._print_result(step, post_result)
            step.hook_event = "PreToolUse"
            if post_result.returncode != 0:
                return False

        return True

    def _run_user_prompt_step(self, step: UserPromptStep) -> bool:
        loader = SchemaLoader("UserPromptSubmit")
        loader.patch({"session_id": self._session_id, "prompt": step.prompt})
        result = run_dispatcher("UserPromptSubmit", loader.to_json())
        self._print_result(step, result)
        return result.returncode == 0

    def _run_stop_step(self, step: StopStep) -> bool:
        loader = SchemaLoader("Stop")
        loader.patch({"session_id": self._session_id})
        result = run_dispatcher("Stop", loader.to_json())
        self._print_result(step, result)
        return result.returncode == 0

    def _print_result(self, step: Step, result: subprocess.CompletedProcess) -> None:
        label = self._step_label(step)
        status = (
            "PASS" if result.returncode == 0 else f"BLOCKED (exit {result.returncode})"
        )
        print(f"[{label}] {status}", flush=True)
        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                print(f"  stdout: {line}", flush=True)
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                print(f"  stderr: {line}", flush=True)

    def _step_label(self, step: Step) -> str:
        if isinstance(step, ToolStep):
            skill = (step.tool_input or {}).get("skill", "?")
            return f"{step.hook_event} Skill({skill})"
        if isinstance(step, UserPromptStep):
            return f"UserPrompt: {step.prompt}"
        if isinstance(step, StopStep):
            return "Stop"
        return step.hook_event

    def reset(self) -> None:
        """Remove sprint state, session state files, and history to start fresh."""
        removed: list[str] = []
        for sprint_dir in SPRINTS_DIR.iterdir():
            if not sprint_dir.is_dir():
                continue
            for name in ("state.json", "state.lock"):
                target = sprint_dir / name
                if target.exists():
                    target.unlink()
                    removed.append(str(target.relative_to(PROJECT_ROOT)))
            sessions_dir = sprint_dir / "sessions"
            if sessions_dir.exists():
                shutil.rmtree(sessions_dir)
                removed.append(str(sessions_dir.relative_to(PROJECT_ROOT)))

        for name in ("history.jsonl", "history.lock"):
            target = SPRINTS_DIR / name
            if target.exists():
                target.unlink()
                removed.append(str(target.relative_to(PROJECT_ROOT)))

        if removed:
            print("=== Reset: removed ===", flush=True)
            for path in removed:
                print(f"  - {path}", flush=True)
        else:
            print("=== Reset: nothing to remove ===", flush=True)

    def run(self) -> None:
        self.reset()
        print(f"=== Dry Run (session: {self._session_id}) ===\n", flush=True)
        for i, step in enumerate(self._steps, 1):
            print(f"Step {i}:", flush=True)
            passed = False
            if isinstance(step, ToolStep):
                passed = self._run_tool_step(step)
            elif isinstance(step, UserPromptStep):
                passed = self._run_user_prompt_step(step)
            elif isinstance(step, StopStep):
                passed = self._run_stop_step(step)
            print(flush=True)
            if not passed:
                print("=== Halted (step blocked) ===", flush=True)
                return
        print("=== Done ===", flush=True)


# Full workflow: /build triggers /implement, then all phases
STEPS: list[Step] = [
    # 1. Build entry point
    UserPromptStep(hook_event="UserPromptSubmit", prompt="/build", timeout=2),
    # 2. Implement a story
    UserPromptStep(
        hook_event="UserPromptSubmit", prompt="/implement TS-013", timeout=2
    ),
    # 3. Explore phase
    ToolStep(tool_input={"skill": "explore"}, timeout=2),
    # 4. Plan phase
    ToolStep(tool_input={"skill": "plan"}, timeout=2),
    # 5. Code phase
    ToolStep(tool_input={"skill": "code"}, timeout=2),
    # 6. Push phase
    ToolStep(tool_input={"skill": "push"}, timeout=2),
    # 7. Log guard — valid calls (PreToolUse only)
    # ToolStep(tool_input={"skill": "log", "args": "story TS-013 completed"}, post=False),
    # # 8. Log guard — invalid calls (should block)
    # ToolStep(tool_input={"skill": "log", "args": "epic T-001 in_progress"}, post=False),
    # ToolStep(tool_input={"skill": "log", "args": "task INVALID completed"}, post=False),
    ToolStep(
        tool_input={"skill": "log", "args": "task T-005 in_progress"},
        post=False,
        timeout=2,
    ),
    # ToolStep(tool_input={"skill": "log", "args": "task T-001"}, post=False),
    # ToolStep(tool_input={"skill": "log"}, post=False),
    # 9. Stop (last — checks story completion)
    StopStep(hook_event="Stop"),
]


SESSION_ID = "58859241-fc2f-41f0-b829-9baac891dd31"

if __name__ == "__main__":
    DryRun(session_id=SESSION_ID, steps=STEPS).run()
