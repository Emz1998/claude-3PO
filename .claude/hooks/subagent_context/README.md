# Subagent Context Hooks

Context injection hooks for subagent spawning.

## Files

**subagent_context.py**

- Hook Event: `PreToolUse`
- Matcher: `Task`
- Injects task logging workflow reminders for engineer subagents

## Behavior

When spawning an engineer subagent, injects context reminding them to:
1. Call `/log:task <task-id> in_progress` before starting work
2. Call `/log:ac <ac-id> met` for each acceptance criteria
3. Call `/log:task <task-id> completed` after all ACs are met

## Engineer Agents

- backend-engineer
- frontend-engineer
- fullstack-developer
- html-prototyper
- react-prototyper
- test-engineer

## Constraint

Only runs when `/build` skill is active (`build_skill_active: true` in cache).

## Dependencies

- `utils` module from `.claude/hooks/utils/`
- `utils.cache` for build status check
- Python 3.10+
