# Input Validation Hooks

Hooks that validate input arguments for tools, skills, and user commands.

## Files

- `skill_args_validator.py` - PreToolUse: Validates Skill tool args for `log:task`, `log:ac`, `log:sc`
- `slash_command_validator.py` - UserPromptSubmit: Validates `/log:*` slash commands

## Skill Args Validator

Validates the `args` parameter format for logging skills before they execute.

**Supported Skills:**
- `log:task` - Expects: `<T###> <status>` where status is: not_started, in_progress, completed, blocked
- `log:ac` - Expects: `<AC-###> <status>` where status is: met, unmet
- `log:sc` - Expects: `<SC-###> <status>` where status is: met, unmet

**Behavior:**
- Blocks with error message if args format is invalid
- Blocks with error message if ID format is invalid
- Blocks with error message if status is invalid
- Exits with 0 (allow) if args are valid or skill is not in scope

## Slash Command Validator

Validates `/log:*` slash commands from user prompts.

**Supported Commands:**
- `/log:task <T###> <status>` - status: not_started, in_progress, completed, blocked
- `/log:ac <AC-###> <status>` - status: met, unmet
- `/log:sc <SC-###> <status>` - status: met, unmet

**Behavior:**
- Shows usage help if command has no args
- Blocks with error if ID format is invalid
- Blocks with error if status is invalid
- Exits with 0 (allow) if valid or not a `/log:*` command

## Hook Registration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          { "type": "command", "command": "python .claude/hooks/input_validation/skill_args_validator.py" }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python .claude/hooks/input_validation/slash_command_validator.py" }
        ]
      }
    ]
  }
}
```
