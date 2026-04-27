"""utils.hooks.post_tool_use — orchestration helpers for the PostToolUse hook.

Extracted from ``dispatchers/post_tool_use.py`` so the dispatcher file holds
only ``main()``. The implement workflow no longer triggers any extra branches
here — the dispatcher hands directly to Recorder.
"""
