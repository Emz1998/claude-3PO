#!/usr/bin/env python3
"""Handlers module for hook entry points.

Consolidated entry points for different hook events:
- user_prompt: UserPromptSubmit handler (workflow activation, dry run)
- pre_tool: PreToolUse handler (routes to guards)
- post_tool: PostToolUse handler (routes to trackers)
- subagent_stop: SubagentStop handler (deliverables enforcement)
"""

from .user_prompt import handle_user_prompt, UserPromptHandler
from .pre_tool import handle_pre_tool, PreToolHandler
from .post_tool import handle_post_tool, PostToolHandler
from .subagent_stop import handle_subagent_stop, SubagentStopHandler

__all__ = [
    # User Prompt
    "handle_user_prompt",
    "UserPromptHandler",
    # Pre Tool
    "handle_pre_tool",
    "PreToolHandler",
    # Post Tool
    "handle_post_tool",
    "PostToolHandler",
    # Subagent Stop
    "handle_subagent_stop",
    "SubagentStopHandler",
]
