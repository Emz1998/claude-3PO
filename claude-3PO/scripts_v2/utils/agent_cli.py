"""subprocess_agents.py — Subprocess wrappers for git and headless agents.

Generic subprocess helpers (``run_git``, ``invoke_headless_agent``) — thin
wrappers around ``subprocess.run`` that swallow errors rather than raise, so
workflow code can treat "agent failed" and "agent said nothing" the same way.
Fail-open by design for the Claude/Codex helpers, because those calls enrich
context rather than gate control.

Public dataclasses (``ClaudeOptions``, ``CodexOptions``, ``InvokeConfig``,
``AgentResponse``) replace the old loose ``**kwargs`` so the agent-flavor
split is type-visible at call sites.
"""

import json
import subprocess
from typing import Annotated, Type, TypeVar, overload
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable
from typing_extensions import Literal


# ---------------------------------------------------------------------------
# Constants + type aliases
# ---------------------------------------------------------------------------


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_TOOLS: tuple[str, ...] = ("Read", "Grep", "Glob")
DEFAULT_SETTINGS_PATH = "/home/emhar/claude-3PO/settings.json"
GIT_TIMEOUT_SECONDS = 30

ConformanceCheck = Callable[[str], tuple[bool, str]]


# ---------------------------------------------------------------------------
# Dataclasses — agent-flavor options + invocation config + parsed response
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClaudeConfig:

    model: str = "haiku"
    bare: bool = False
    tools: tuple[str, ...] = DEFAULT_TOOLS
    allowed_tools: tuple[str, ...] | None = None
    output_format: str = "text"
    settings: str = DEFAULT_SETTINGS_PATH
    session_id: str | None = None
    json_output: bool = False


@dataclass(frozen=True, slots=True)
class CodexConfig:

    session_id: str | None = None
    output_schema: dict[str, Any] | None = None
    json_output: bool = False
    model: str | None = None


AgentConfig = Annotated[ClaudeConfig | CodexConfig, Literal["codex", "claude"]]


@dataclass(frozen=True, slots=True)
class AgentResponse:

    session_id: str
    text: str
    raw: str


# ---------------------------------------------------------------------------
# Argv builders — one per agent flavor, dispatched by option type
# ---------------------------------------------------------------------------


def _build_claude_argv(prompt: str, options: ClaudeConfig) -> list[str]:
    argv: list[str] = ["claude"]
    if options.bare:
        argv.append("--bare")
    argv.extend(["-p", prompt])
    argv.extend(["--tools", ",".join(options.tools)])
    argv.extend(["--output-format", options.output_format])
    argv.extend(["--model", options.model])
    argv.extend(["--settings", options.settings])
    # Session resume is optional; only wire the flag when the caller pinned a session.
    if options.allowed_tools:
        argv.extend(["--allowedTools", ",".join(options.allowed_tools)])
    if options.session_id:
        argv.extend(["--session-id", options.session_id])
    if options.json_output:
        argv.append("--json")
    return argv


def _build_codex_argv(options: CodexConfig) -> list[str]:
    argv = ["codex", "exec", "--skip-git-repo-check"]
    if options.json_output:
        argv.append("--json")
    if options.output_schema:
        argv.extend(["--output-schema", json.dumps(options.output_schema)])
    if options.session_id:
        argv.extend(["resume", options.session_id])
    # Trailing `-` tells codex to read the prompt from stdin.
    argv.append("-")
    return argv


def _build_argv(prompt: str, options: object) -> list[str]:
    if isinstance(options, ClaudeConfig):
        return _build_claude_argv(prompt, options)
    if isinstance(options, CodexConfig):
        return _build_codex_argv(options)
    raise TypeError(f"Unknown agent options type: {type(options).__name__}")


# ---------------------------------------------------------------------------
# Headless agent invocation
# ---------------------------------------------------------------------------


def _try_invoke(
    prompt: str,
    config: AgentConfig,
    timeout: int,
    cwd: Path | None,
) -> str | None:

    argv = _build_argv(prompt, config)
    try:
        # Pipe prompt on stdin too — codex requires it, claude tolerates it.
        result = subprocess.run(
            argv,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    # Empty stdout counts as failure — callers expect meaningful content or None.
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def run_headless(
    prompt: str,
    config: AgentConfig,
    *,
    timeout: int,
    cwd: Path | None = None,
) -> str | None:
    out = _try_invoke(prompt, config, timeout, cwd)
    # Claude-only fallback: retry once without --bare if the bare call returned nothing.
    if out is None and isinstance(config, ClaudeConfig) and config.bare:
        out = _try_invoke(prompt, replace(config, bare=False), timeout, cwd)
    return out


# ---------------------------------------------------------------------------
# JSONL response parsing
# ---------------------------------------------------------------------------


def parse_agent_response(raw: str) -> AgentResponse:
    session_id = ""
    text = ""
    # One scan: take first populated thread_id, overwrite text so last chunk wins.
    for line in raw.split("\n"):
        if not line.startswith("{"):
            continue
        data = json.loads(line)
        if not session_id:
            session_id = data.get("thread_id", "") or ""
        item_text = data.get("item", {}).get("text", "")
        if item_text:
            text = item_text
    return AgentResponse(session_id=session_id, text=text, raw=raw)


# ---------------------------------------------------------------------------
# Self-correcting agent loop
# ---------------------------------------------------------------------------


def _collect_feedback(text: str, checks: list[ConformanceCheck]) -> str:
    messages = [msg for ok, msg in (c(text) for c in checks) if not ok]
    return "\n".join(messages)


CONFIG_MAP: dict[Literal["codex", "claude"], Type[AgentConfig]] = {
    "codex": CodexConfig,
    "claude": ClaudeConfig,
}


@overload
def invoke_agent(
    prompt: str,
    llm: Literal["claude"],
    config: ClaudeConfig,
    *,
    conformance_checks: list[ConformanceCheck] | None = None,
    attempts_remaining: int = DEFAULT_MAX_ATTEMPTS,
) -> str: ...


@overload
def invoke_agent(
    prompt: str,
    llm: Literal["codex"],
    config: CodexConfig,
    *,
    conformance_checks: list[ConformanceCheck] | None = None,
    attempts_remaining: int = DEFAULT_MAX_ATTEMPTS,
) -> str: ...


def invoke_agent(
    prompt: str,
    llm: Literal["codex", "claude"],
    config: AgentConfig,
    *,
    conformance_checks: list[ConformanceCheck] | None = None,
    attempts_remaining: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    return _invoke_agent(prompt, llm, config, conformance_checks, attempts_remaining)


def _invoke_agent(
    prompt: str,
    llm: Literal["codex", "claude"],
    config: AgentConfig,
    conformance_checks: list[ConformanceCheck] | None,
    attempts_remaining: int,
) -> str:

    # One invocation → parse → (maybe) recurse.
    raw = run_headless(prompt, config, timeout=DEFAULT_TIMEOUT_SECONDS)
    if raw is None:
        return f"{llm} {config.model} failed to respond"
    response = parse_agent_response(raw)
    if not response.session_id:
        return f"{llm} {config.model} failed to get session id"
    if not conformance_checks:
        return response.text
    feedback = _collect_feedback(response.text, conformance_checks)
    # Stop when checks pass or the retry budget is exhausted.
    if not feedback or attempts_remaining <= 1:
        return response.text
    # Resume the pinned session and recurse with one fewer attempt.
    next_config: AgentConfig = replace(config, session_id=response.session_id)
    return _invoke_agent(
        feedback, llm, next_config, conformance_checks, attempts_remaining - 1
    )
