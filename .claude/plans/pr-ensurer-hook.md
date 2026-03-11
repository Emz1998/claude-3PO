# PR Ensurer Hook — Implementation Plan

## Context
We need a hook that prevents Claude from stopping when no PR has been created during an active workflow session. This ensures code changes always result in a PR before the session ends. The `pr_created` state is tracked via the existing `StateStore` and checked in the existing `stop_guard.py`.

## Files to Modify

### 1. `.claude/hooks/workflow/handlers/recorder.py`
**Purpose**: Record `pr_created: True` when a PR creation command is detected.

Add a `"Bash"` case to the existing `main()` match block that checks if the command contains `gh pr create` or `pr_manager.py create`:

```python
case "Bash":
    command = hook_input.tool_input.command
    if "gh pr create" in command or "pr_manager.py create" in command:
        record("pr_created", True)
```

This reuses the existing `record()` helper and `STATE_STORE` already in the file.

### 2. `.claude/hooks/workflow/guards/stop_guard.py`
**Purpose**: Block stoppage when `pr_created` is not True.

Add `is_pr_created()` method to `StopGuard`:

```python
def is_pr_created(self) -> bool:
    state = StateStore(state_path=cfg("paths.workflow_state"))
    return state.get("pr_created", False) is True
```

Update `run()` to check PR state after story completion check:

```python
def run(self) -> None:
    if not self._is_workflow_active:
        return

    is_completed, story_id = self.is_story_completed()
    if not is_completed:
        Hook.block(f"Story '{story_id}' is not completed.")

    if not self.is_pr_created():
        Hook.block("PR has not been created. Create a PR before stopping.")
```

### 3. No new files or hook registrations
- `recorder.py` is already registered as a PostToolUse hook in `settings.local.json`
- `stop_guard.py` is already registered as a Stop hook in `settings.local.json`

## Verification
1. Test recorder detects PR creation:
   ```
   echo '<bash PostToolUse JSON with "gh pr create" command>' | python3 .claude/hooks/workflow/handlers/recorder.py
   ```
   Then verify `pr_created: true` in `state.json`

2. Test stop guard blocks when no PR:
   - Set `workflow_active: true` and `pr_created: false` in state
   - Run stop guard — should exit code 2 (block)

3. Test stop guard passes when PR created:
   - Set `pr_created: true` in state
   - Run stop guard — should exit code 0
