# Trackers

PostToolUse hooks that record state changes after successful tool execution.

## Files

| File | Purpose |
|------|---------|
| `phase_tracker.py` | Records current phase when a Skill (phase transition) executes |
| `deliverables_tracker.py` | Marks deliverables complete on Write/Edit/Read/Bash tool use |
| `release_plan_tracker.py` | Validates and records `/log:task`, `/log:ac`, `/log:sc` commands |

## Key Classes

| Class | Triggers On | Records |
|-------|------------|---------|
| `PhaseTracker` | Skill tool | `current_phase` in state |
| `DeliverableTracker` | Write, Edit, Read, Bash | Deliverable completion status |
| `ReleasePlanTracker` | Skill (`/log:*`) | Task completions, AC/SC status |

## Tracker Contract

Trackers record state but never block operations:

```python
class MyTracker:
    def is_active(self) -> bool:
        return self._state.is_workflow_active()

    def run(self, hook_input: dict) -> None:
        if not self.is_active():
            return
        # Recording logic (no exit codes, no blocking)
```

## Validation Chain

The `ReleasePlanTracker` triggers validation checks after recording:
1. Task completed -> sets `needs_ac_validation` if all user story tasks done
2. AC met -> sets `needs_sc_validation` if all feature ACs met
3. SC met -> sets `needs_epic_sc_validation` if all epic SCs met
