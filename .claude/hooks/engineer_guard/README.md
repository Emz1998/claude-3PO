# Engineer Task Guard

Ensures engineer agents complete their assigned tasks before stopping.

**Constraint:** Only runs when `/build` skill is active.

## Engineer Agents

- backend-engineer
- frontend-engineer
- fullstack-developer
- html-prototyper
- react-prototyper
- test-engineer

## Enforcement

- Blocks all tools until task is `in_progress` in roadmap
- Prevents SubagentStop until task is `completed` in roadmap
- Always allows `/log:task` skill for status updates
- Falls back to roadmap if cache is empty

## Race Condition Handling

- Task ID captured at activation and stored in cache
- Uses stored task ID (not current) to prevent drift when roadmap advances
- Graceful degradation when roadmap unreadable

## Usage

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "python3 .claude/hooks/engineer_guard/engineer_task_guard.py",
        "timeout": 5000
      }
    ],
    "SubagentStop": [
      {
        "command": "python3 .claude/hooks/engineer_guard/engineer_task_guard.py",
        "timeout": 5000
      }
    ]
  }
}
```
