#!/usr/bin/env python3
"""summarize_prompt.py — UserPromptSubmit async hook.

Parses the user prompt for /build <instructions>, runs headless Claude
to summarize, writes prompt_summary to state, and resolves any
'Pending...' entries in violations.md.

Runs with async:true in hooks.json — non-blocking.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.hook import Hook
from utils.state_store import StateStore
from utils.violations import resolve_pending_summaries, VIOLATIONS_PATH

STATE_PATH = Path(__file__).resolve().parent / "state.jsonl"

# Match /build or claudeguard:build at start of prompt, capture the rest
BUILD_PATTERN = re.compile(r"^/(?:\w+:)?build\s+(.*)", re.DOTALL)

# Flags to strip from instructions
FLAGS = [
    "--skip-explore",
    "--skip-research",
    "--skip-all",
    "--tdd",
    "--reset",
    "--takeover",
]
STORY_ID_PATTERN = r"\b([A-Z]{2,}-\d+)\b"


def extract_build_instructions(prompt: str) -> str | None:
    """Extract instructions from a /build prompt. Returns None if not a /build."""
    match = BUILD_PATTERN.match(prompt.strip())
    if not match:
        return None

    text = match.group(1)
    # Strip flags and story IDs
    text = re.sub(STORY_ID_PATTERN, "", text)
    for flag in FLAGS:
        text = text.replace(flag, "")
    return text.strip() or None


def summarize(instructions: str) -> str:
    """Use headless Claude to generate a short summary."""
    prompt = (
        "Summarize the following task instructions in one short sentence (under 60 characters). "
        "Respond with ONLY the summary, nothing else.\n\n"
        f"Instructions: {instructions}"
    )

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--output-format",
                "text",
                "--tools" "Read, Grep, Glob",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            summary = result.stdout.strip()
            return summary[:80] if len(summary) > 80 else summary
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: first 60 chars of instructions
    return instructions[:60] if len(instructions) > 60 else instructions


def main() -> None:
    hook_input = Hook.read_stdin()

    session_id = hook_input.get("session_id", "")
    if not session_id:
        sys.exit(0)

    prompt = hook_input.get("prompt", "")
    if not prompt:
        sys.exit(0)

    # Only process /build prompts — implement uses story_id (N/A for summary)
    instructions = extract_build_instructions(prompt)
    if not instructions:
        sys.exit(0)

    # Check if session is active
    state = StateStore(STATE_PATH, session_id=session_id)
    if not state.get("workflow_active"):
        sys.exit(0)
    if state.get("workflow_type") != "build":
        sys.exit(0)

    summary = summarize(instructions)

    # Write to state
    state.set("prompt_summary", summary)

    # Resolve pending violations
    resolve_pending_summaries(VIOLATIONS_PATH, session_id, summary)

    sys.exit(0)


if __name__ == "__main__":
    main()
