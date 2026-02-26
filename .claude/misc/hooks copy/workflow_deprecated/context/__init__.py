#!/usr/bin/env python3
"""Context module for workflow context injection.

Contains components for injecting phase-specific context and reminders:
- phase_reminders: Phase reminder content definitions (loaded from external files)
- context_injector: Injects reminders via PostToolUse
"""

from .phase_reminders import (
    get_phase_reminder,
    get_all_phase_reminders,
    get_available_phases,
    clear_cache,
)
from .context_injector import inject_phase_context, ContextInjector

__all__ = [
    # Phase Reminders
    "get_phase_reminder",
    "get_all_phase_reminders",
    "get_available_phases",
    "clear_cache",
    # Context Injector
    "inject_phase_context",
    "ContextInjector",
]
