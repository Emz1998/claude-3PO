# Reminders

Phase-specific reminder content injected into agent context during workflow execution.

## Files

Each markdown file corresponds to a workflow phase and contains guidance text loaded by `context/phase_reminders.py`:

| File | Phase |
|------|-------|
| `explore.md` | Codebase exploration |
| `plan.md` | Implementation planning |
| `plan-consult.md` | Plan review and consultation |
| `finalize-plan.md` | Plan finalization |
| `write-test.md` | Test writing (TDD red phase) |
| `review-test.md` | Test review |
| `write-code.md` | Code implementation (TDD green phase) |
| `code-review.md` | Code review |
| `refactor.md` | Code refactoring (TDD refactor phase) |
| `validate.md` | Validation |
| `commit.md` | Commit preparation |

## How It Works

1. `phase_reminders.py` loads the markdown file matching the current phase
2. `context_injector.py` injects the content as a system reminder after phase transitions
3. Content guides the agent on what to focus on during that phase

## Adding a New Reminder

Create a new `<phase-name>.md` file in this directory. It will be automatically loaded when the corresponding phase is active.
