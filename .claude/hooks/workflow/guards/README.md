# Guards

PreToolUse and Stop validation hooks that enforce workflow rules by blocking invalid operations.

## Files

| File | Purpose |
|------|---------|
| `phase_transition.py` | Validates phase transitions follow the defined order |
| `subagent_access.py` | Validates the correct subagent is used for the current phase |
| `deliverables_exit.py` | Blocks SubagentStop if phase deliverables are incomplete |
| `task_dod_stop.py` | Blocks Stop if current tasks are not all completed |

## Key Classes

| Class | Hook Event | Blocks When |
|-------|-----------|-------------|
| `PhaseTransitionGuard` | PreToolUse (Skill) | Phase skipped or reversed |
| `SubagentAccessGuard` | PreToolUse (Task) | Wrong subagent for phase |
| `DeliverablesExitGuard` | SubagentStop | Incomplete deliverables |
| `TaskDodStopGuard` | Stop | Tasks with status != "completed" |

## Guard Contract

All guards follow the same pattern:

```python
class MyGuard:
    def is_active(self) -> bool:
        return self._state.is_workflow_active()

    def run(self, hook_input: dict) -> None:
        if not self.is_active():
            return
        # Validation logic
        if invalid:
            print("Error message", file=sys.stderr)
            sys.exit(2)  # Block the operation
```

- `exit(0)` or return = allow
- `exit(2)` + stderr = block with error message
