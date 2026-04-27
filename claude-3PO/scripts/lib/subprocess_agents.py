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
class ClaudeOptions:
    """Options for a headless Claude (``claude -p``) invocation.

    Frozen so the bare-retry path can use ``dataclasses.replace`` to flip
    one field without mutating a shared instance.

    Args:
        model (str): Claude model alias (e.g. ``haiku``).
        bare (bool): Emit ``--bare`` on the first attempt; a fallback
            without ``--bare`` is automatic on failure.
        tools (tuple[str, ...]): Tools exposed to the agent.
        allowed_tools (tuple[str, ...]): Allowlist for ``--allowedTools``.
        output_format (str): ``text`` or ``json``.
        settings (str): Path to the settings file.
        session_id (str | None): Resume an existing session when set.

    Example:
        >>> ClaudeOptions(model="haiku").output_format
        'text'
        Return: 'text'
    """

    model: str = "haiku"
    bare: bool = False
    tools: tuple[str, ...] = DEFAULT_TOOLS
    allowed_tools: tuple[str, ...] = DEFAULT_TOOLS
    output_format: str = "text"
    settings: str = DEFAULT_SETTINGS_PATH
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class CodexOptions:
    """Options for a headless Codex (``codex exec``) invocation.

    The prompt is *not* a field here — it is delivered via stdin by the
    caller (``subprocess.run(..., input=prompt)``) because ``codex exec``
    reads its prompt from the trailing ``-`` sentinel.

    Args:
        session_id (str | None): Resume an existing codex session (appends
            ``resume <session_id>``).
        output_schema (dict | None): JSON schema forwarded via
            ``--output-schema``.
        json_output (bool): Append ``--json`` for structured JSONL events.
        model (str | None): Reserved for future per-call model selection;
            unused today since codex picks its model by config.

    Example:
        >>> CodexOptions(json_output=True).json_output
        True
        Return: True
    """

    session_id: str | None = None
    output_schema: dict[str, Any] | None = None
    json_output: bool = False
    model: str | None = None


AgentOptions = ClaudeOptions | CodexOptions


@dataclass(frozen=True, slots=True)
class InvokeConfig:
    """Config bundle for a self-correcting :func:`invoke_agent` call.

    Keeping the config frozen lets the retry path synthesize the next
    config with ``dataclasses.replace`` without mutating the caller's
    copy. ``conformance_checks`` stays outside this struct because it
    holds callables, not data.

    Args:
        llm (Literal["codex", "claude"]): Target agent flavor.
        model (str | None): Model alias (defaults to the agent's default).
        session_id (str | None): Resume an existing session when set.
        timeout (int): Seconds before the subprocess is killed.
        attempts_left (int): Remaining correction rounds including this one.

    Example:
        >>> InvokeConfig(llm="codex").timeout
        60
        Return: 60
    """

    llm: Literal["codex", "claude"]
    model: str | None = None
    session_id: str | None = None
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    attempts_left: int = DEFAULT_MAX_ATTEMPTS


@dataclass(frozen=True, slots=True)
class AgentResponse:
    """Parsed JSONL payload from a headless agent.

    ``raw`` is retained alongside the parsed fields so callers that need
    the full stream (e.g. for debugging failed conformance rounds) don't
    have to re-request it.

    Args:
        session_id (str): ``thread_id`` pin for resume; empty if absent.
        text (str): Last non-empty ``item.text`` emitted by the agent.
        raw (str): Original stdout blob.

    Example:
        >>> AgentResponse(session_id="sid", text="t", raw="r").session_id
        'sid'
        Return: 'sid'
    """

    session_id: str
    text: str
    raw: str


# ---------------------------------------------------------------------------
# git wrapper
# ---------------------------------------------------------------------------


def run_git(
    args: list[str], cwd: Path, timeout: int = GIT_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess:
    """
    Run ``git <args>`` inside *cwd* and return the result without raising.

    A timeout is mandatory in practice: the auto-commit hook and the
    PostToolUse path both call this synchronously and would otherwise hang
    the live session on a stuck git operation (e.g. a credential prompt
    with no TTY). On timeout we return a synthesized non-zero result so
    callers that check ``returncode`` fall through their error branch
    instead of seeing a raised exception.

    Args:
        args (list[str]): Argv tail (everything after ``git``).
        cwd (Path): Working directory for the git invocation.
        timeout (int): Max seconds before the subprocess is killed.

    Returns:
        subprocess.CompletedProcess: Fully populated result; callers inspect
        ``returncode``, ``stdout``, and ``stderr`` themselves.

    Example:
        >>> run_git(["status", "--porcelain"], Path.cwd())  # doctest: +SKIP
        Return: CompletedProcess(args=['git', 'status', '--porcelain'], returncode=0, ...)
    """
    try:
        # Capture text so callers can parse stdout/stderr without decoding bytes.
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        # Synthesize a non-zero result so callers treat timeout like any other git failure.
        return subprocess.CompletedProcess(
            args=e.cmd, returncode=124, stdout="", stderr=f"git timed out after {timeout}s",
        )


# ---------------------------------------------------------------------------
# Argv builders — one per agent flavor, dispatched by option type
# ---------------------------------------------------------------------------


def _build_claude_argv(prompt: str, options: ClaudeOptions) -> list[str]:
    """
    Build argv for a headless Claude invocation from *options*.

    Args:
        prompt (str): Prompt text passed via ``-p`` (also streamed on stdin
            by the caller so both delivery paths stay identical).
        options (ClaudeOptions): Flavor-specific flags.

    Returns:
        list[str]: Subprocess argv starting with ``claude``.

    Example:
        >>> _build_claude_argv("hi", ClaudeOptions())[:3]
        ['claude', '-p', 'hi']
        Return: ['claude', '-p', 'hi']
    """
    # Start with the binary and opt-in flags only — keeps argv free of empty strings.
    argv: list[str] = ["claude"]
    if options.bare:
        argv.append("--bare")
    argv.extend(["-p", prompt])
    argv.extend(["--tools", ",".join(options.tools)])
    argv.extend(["--allowedTools", ",".join(options.allowed_tools)])
    argv.extend(["--output-format", options.output_format])
    argv.extend(["--model", options.model])
    argv.extend(["--settings", options.settings])
    # Session resume is optional; only wire the flag when the caller pinned a session.
    if options.session_id:
        argv.extend(["--session-id", options.session_id])
    return argv


def _build_codex_argv(options: CodexOptions) -> list[str]:
    """
    Build argv for a headless Codex invocation from *options*.

    The prompt is not positional here — it's read from stdin via the
    trailing ``-`` sentinel, so the caller wires it up with ``input=prompt``.

    Args:
        options (CodexOptions): Flavor-specific flags.

    Returns:
        list[str]: Subprocess argv ending in ``-`` (stdin sentinel).

    Example:
        >>> _build_codex_argv(CodexOptions())[:3]
        ['codex', 'exec', '--skip-git-repo-check']
        Return: ['codex', 'exec', '--skip-git-repo-check', '-']
    """
    # Skip the git-repo check so codex runs from any cwd the hook picked.
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
    """
    Dispatch to the per-agent argv builder by option type.

    Typing on the options dataclass (not a magic ``"claude"``/``"codex"``
    string) means unknown flavors fail at construction time, not here.
    The parameter is annotated ``object`` (not the narrow ``AgentOptions``
    union) so the runtime ``TypeError`` branch stays reachable under
    strict type-checkers when callers hand us something outside the
    union (e.g. a raw dict).

    Args:
        prompt (str): Prompt text (only used by the claude builder).
        options (object): Expected to be ``ClaudeOptions`` or ``CodexOptions``.

    Returns:
        list[str]: Subprocess argv ready for ``subprocess.run``.

    Raises:
        TypeError: When *options* is neither ``ClaudeOptions`` nor ``CodexOptions``.

    Example:
        >>> _build_argv("hi", ClaudeOptions())[:2]
        ['claude', '-p']
        Return: ['claude', '-p']
    """
    if isinstance(options, ClaudeOptions):
        return _build_claude_argv(prompt, options)
    if isinstance(options, CodexOptions):
        return _build_codex_argv(options)
    raise TypeError(f"Unknown agent options type: {type(options).__name__}")


# ---------------------------------------------------------------------------
# Headless agent invocation
# ---------------------------------------------------------------------------


def _try_invoke(
    prompt: str, options: AgentOptions, timeout: int, cwd: Path | None,
) -> str | None:
    """
    Run a single subprocess attempt for a headless agent.

    Separated from :func:`invoke_headless_agent` so the bare-retry path
    re-uses the same "build-argv-then-run" sequence without duplicating
    the fail-open rules.

    Args:
        prompt (str): Prompt text; also piped to the process on stdin.
        options (AgentOptions): Flavor-specific flags.
        timeout (int): Max seconds before the subprocess is killed.
        cwd (Path | None): Working directory; ``None`` uses the current.

    Returns:
        str | None: Stripped stdout on success, ``None`` on any failure.

    Raises:
        TypeError: When *options* is an unknown type.

    Example:
        >>> _try_invoke("hi", ClaudeOptions(), 10, None)  # doctest: +SKIP
        Return: 'ok'
    """
    argv = _build_argv(prompt, options)
    try:
        # Pipe prompt on stdin too — codex requires it, claude tolerates it.
        result = subprocess.run(
            argv, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    # Empty stdout counts as failure — callers expect meaningful content or None.
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def invoke_headless_agent(
    prompt: str,
    options: AgentOptions,
    *,
    timeout: int,
    cwd: Path | None = None,
) -> str | None:
    """
    Invoke a headless Claude or Codex agent and return its stdout.

    The helper fail-opens: any non-zero exit, empty stdout, missing binary,
    or timeout yields ``None``, so callers that use agents to *enrich*
    context can treat "nothing came back" and "the call failed" identically.

    When *options* is a :class:`ClaudeOptions` with ``bare=True``, a single
    retry is attempted with ``bare=False`` on failure — ``--bare`` strips
    features that some claude builds reject outright, so a second pass
    with the full argv recovers the call without pushing the dance onto
    every caller.

    Args:
        prompt (str): Prompt text; also streamed on stdin for both agents.
        options (AgentOptions): Flavor-specific flags (see module docstring).
        timeout (int): Max seconds before the subprocess is killed.
        cwd (Path | None): Working directory; ``None`` uses the current.

    Returns:
        str | None: Stripped stdout on success (from first or fallback
        attempt), ``None`` when both attempts fail.

    Raises:
        TypeError: When *options* is an unknown type.

    Example:
        >>> invoke_headless_agent("Review this plan", ClaudeOptions(), timeout=60)  # doctest: +SKIP
        Return: 'feat: add thing'
    """
    # First attempt with caller's exact options.
    out = _try_invoke(prompt, options, timeout, cwd)
    # Claude-only fallback: retry once without --bare if the bare call returned nothing.
    if out is None and isinstance(options, ClaudeOptions) and options.bare:
        out = _try_invoke(prompt, replace(options, bare=False), timeout, cwd)
    return out


# ---------------------------------------------------------------------------
# JSONL response parsing
# ---------------------------------------------------------------------------


def parse_agent_response(raw: str) -> AgentResponse:
    """
    Parse a JSONL agent stdout blob into session id + final text.

    Agents emit one JSON object per line: the first populated
    ``thread_id`` pins the session for resumable correction rounds, and
    the *last* non-empty ``item.text`` is the completed answer (earlier
    lines are status / partial text chunks).

    Args:
        raw (str): Raw agent stdout (line-delimited JSON; non-JSON lines
            are skipped so banner/noise lines don't break parsing).

    Returns:
        AgentResponse: ``session_id`` and ``text`` (empty strings when
        absent), plus the original ``raw`` for debugging.

    Raises:
        json.JSONDecodeError: If a ``{``-prefixed line is not valid JSON.

    Example:
        >>> parse_agent_response('{"thread_id":"abc"}\\n{"item":{"text":"t"}}\\n').session_id
        'abc'
        Return: 'abc'
    """
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


def _config_to_options(config: InvokeConfig) -> AgentOptions:
    """
    Translate an :class:`InvokeConfig` into flavor-specific agent options.

    The self-correcting loop always needs JSONL output so it can extract
    a session id for the retry round, which is why ``output_format=json``
    / ``json_output=True`` are forced here rather than exposed on
    :class:`InvokeConfig`.

    Args:
        config (InvokeConfig): Caller-supplied invocation config.

    Returns:
        AgentOptions: ``ClaudeOptions`` or ``CodexOptions`` with the JSONL
        flags forced on.

    Example:
        >>> _config_to_options(InvokeConfig(llm="codex")).json_output
        True
        Return: True
    """
    if config.llm == "claude":
        # Claude uses --output-format json for JSONL.
        return ClaudeOptions(
            model=config.model or "haiku",
            output_format="json",
            session_id=config.session_id,
        )
    # Codex uses --json for JSONL.
    return CodexOptions(
        json_output=True, session_id=config.session_id, model=config.model,
    )


def _collect_feedback(text: str, checks: list[ConformanceCheck]) -> str:
    """
    Run every conformance check and join the feedback from failures.

    Joining with a newline means the next correction prompt carries every
    outstanding gripe in one round rather than one-per-pass.

    Args:
        text (str): Agent response text to check.
        checks (list[ConformanceCheck]): Checks to run.

    Returns:
        str: Joined feedback from failing checks (empty if all passed).

    Example:
        >>> _collect_feedback("r", [lambda _: (False, "x")])
        'x'
        Return: 'x'
    """
    # Iterate once; keep only feedback from failing checks.
    messages = [msg for ok, msg in (c(text) for c in checks) if not ok]
    return "\n".join(messages)


def invoke_agent(
    prompt: str,
    config: InvokeConfig,
    *,
    conformance_checks: list[ConformanceCheck] | None = None,
) -> str:
    """
    Run a self-correcting, format-agnostic agent via a headless agent.

    One round: invoke → parse → run conformance checks → recurse with the
    joined feedback and a resumed session, until checks pass or
    ``attempts_left`` hits 1. Returns the last observed response text on
    success, or a sentinel string (``"<llm> <model> failed…"``) on agent
    failure — callers treat sentinels like real responses (the fail-open
    convention shared across this module).

    Args:
        prompt (str): Initial (or correction) prompt text.
        config (InvokeConfig): Frozen invocation config; the retry path
            uses ``dataclasses.replace`` to pin the session and decrement
            ``attempts_left``.
        conformance_checks (list[ConformanceCheck] | None): Optional
            checks; when ``None`` the first response is returned as-is.

    Returns:
        str: Final agent response text, or a failure sentinel.

    Raises:
        json.JSONDecodeError: If the agent emits malformed JSONL.

    Example:
        >>> invoke_agent("p", InvokeConfig(llm="codex"))  # doctest: +SKIP
        Return: '...'
    """
    # One invocation → parse → (maybe) recurse.
    options = _config_to_options(config)
    raw = invoke_headless_agent(prompt, options, timeout=config.timeout)
    if raw is None:
        return f"{config.llm} {config.model} failed to respond"
    resp = parse_agent_response(raw)
    if not resp.session_id:
        return f"{config.llm} {config.model} failed to get session id"
    if not conformance_checks:
        return resp.text
    feedback = _collect_feedback(resp.text, conformance_checks)
    # Stop when checks pass or the retry budget is exhausted.
    if not feedback or config.attempts_left <= 1:
        return resp.text
    # Resume the pinned session and recurse with one fewer attempt.
    next_config = replace(
        config, session_id=resp.session_id, attempts_left=config.attempts_left - 1,
    )
    return invoke_agent(feedback, next_config, conformance_checks=conformance_checks)
