"""Tests for handlers/ registry — import smoke, completeness, type checks."""

import pytest
from typing import Any, Callable


def test_all_handlers_importable():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    # Should not raise ImportError
    assert isinstance(HANDLER_REGISTRY, dict)


def test_all_four_events_have_handlers():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    expected_events = {"PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"}
    assert set(HANDLER_REGISTRY.keys()) == expected_events


def test_each_event_has_at_least_one_handler():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    for event, handlers in HANDLER_REGISTRY.items():
        assert len(handlers) >= 1, f"Event '{event}' has no handlers"


def test_pre_tool_use_handlers():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    names = [h.__module__.split(".")[-1] for h in HANDLER_REGISTRY["PreToolUse"]]
    assert "phase_guard" in names
    assert "log_guard" in names
    assert "commit_guard" in names


def test_post_tool_use_handlers():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    names = [h.__module__.split(".")[-1] for h in HANDLER_REGISTRY["PostToolUse"]]
    assert "session_recorder" in names
    assert "logging_reminder" in names
    assert "parallel_tasks" in names


def test_user_prompt_submit_handlers():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    names = [h.__module__.split(".")[-1] for h in HANDLER_REGISTRY["UserPromptSubmit"]]
    assert "build_entry" in names
    assert "implement_trigger" in names


def test_stop_handlers():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    names = [h.__module__.split(".")[-1] for h in HANDLER_REGISTRY["Stop"]]
    assert "stop_guard" in names


def test_all_handlers_are_callable():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    for event, handlers in HANDLER_REGISTRY.items():
        for handler in handlers:
            assert callable(handler), f"Handler {handler} for '{event}' is not callable"


def test_all_handlers_named_handle():
    from scripts.claude_hooks.handlers import HANDLER_REGISTRY

    for event, handlers in HANDLER_REGISTRY.items():
        for handler in handlers:
            assert handler.__name__ == "handle", (
                f"Handler {handler.__module__} for '{event}' should be named 'handle', "
                f"got '{handler.__name__}'"
            )


def test_get_handlers_returns_list():
    from scripts.claude_hooks.handlers import get_handlers

    result = get_handlers("PreToolUse")
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_handlers_unknown_event_returns_empty():
    from scripts.claude_hooks.handlers import get_handlers

    result = get_handlers("NonExistentEvent")
    assert result == []
