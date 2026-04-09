"""recorder.py — All state-mutation (recording) logic for workflow hooks.

Guards handle validation (allow/block). This module handles recording:
tracking agents, files, phases, scores, and other state changes that
happen after a tool use is allowed.

Usage:
    python3 recorder.py --hook-input '{"hook_event_name":"PostToolUse",...}'

Environment:
    RECORDER_STATE_PATH — override the default state.json path
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import (
    DEFAULT_STATE_JSONL_PATH,
    PLAN_REVIEW_THRESHOLD,
    PLAN_REVIEW_MAX,
    CODE_REVIEW_THRESHOLD,
    CODE_REVIEW_MAX,
)
from scripts.state_store import StateStore
from scripts.logger import log
from scripts.hook import HookInput


# ---------------------------------------------------------------------------
# Agent recording
# ---------------------------------------------------------------------------


def record_agent_invocation(
    store: StateStore, agent_type: str, tool_use_id: str
) -> None:
    """Append an agent entry as 'running' to state.agents[]."""

    def _update(state: dict) -> None:
        state.setdefault("agents", []).append(
            {
                "agent_type": agent_type,
                "status": "running",
                "tool_use_id": tool_use_id,
            }
        )

    store.update(_update)


def record_agent_stoppage(store: StateStore, agent_type: str, tool_use_id: str) -> None:
    """Append an agent entry as 'completed' to state.agents[]."""

    def _update(state: dict) -> None:
        agents = state.get("agents", [])
        for agent in agents:
            if (
                agent.get("agent_type") == agent_type
                and agent.get("tool_use_id") == tool_use_id
            ):
                agent["status"] = "completed"
                break
        state["agents"] = agents

    store.update(_update)


def record_agent(hook_input: HookInput, store: StateStore) -> None:

    hook_event_name = hook_input.hook_event_name

    if hook_event_name == "PreToolUse":
        if hook_input.tool_name == "Agent":
            tool_use_id = hook_input.tool_use_id
            agent_type = hook_input.subagent_type

            record_agent_invocation(store, agent_type, tool_use_id)

    elif hook_event_name == "Stop":
        if hook_input.tool_name == "Agent":
            tool_use_id = hook_input.tool_use_id
            agent_type = hook_input.agent_type

            record_agent_stoppage(store, agent_type, tool_use_id)
