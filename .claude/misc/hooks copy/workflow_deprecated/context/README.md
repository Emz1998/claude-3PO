# Context

Phase-specific context injection into agent conversations after tool execution.

## Files

| File | Purpose |
|------|---------|
| `phase_reminders.py` | Loads phase reminder content from `config/reminders/` with caching |
| `context_injector.py` | PostToolUse hook that injects phase reminders and validation context |

## Key Exports

- `ContextInjector` - Class that handles context injection after tool use
- `get_phase_reminder(phase)` - Get reminder content for a specific phase
- `get_all_phase_reminders()` - Get all available phase reminders
- `inject_phase_context()` - Function-based entry point for context injection
- `clear_cache()` - Clear the reminder content cache

## Flow

1. After a Skill tool executes (phase transition), the `PostToolHandler` calls `ContextInjector`
2. `ContextInjector` checks the current phase and loads the corresponding reminder
3. If `pending_validation` is set in state, validation-specific context is injected instead
4. The reminder content is printed to stdout for Claude to include in its context
