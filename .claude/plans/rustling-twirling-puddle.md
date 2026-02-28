# Plan: Fix `/implement` Default Behavior with Task Range Validation

## Problem Statement

1. `/implement` without args should default to current tasks from `project/state.json`
2. `/implement TNNN` or `/implement TNNN - TNNN` must validate task IDs are in `current_tasks`
3. Out-of-range or completed tasks should be blocked with an error
4. `/implement --help` should show available tasks from current_tasks

## Current State Example

```json
{
  "current_tasks": {
    "T009": "not_started",
    "T010": "not_started"
  },
  "completed_tasks": ["T001", "T002", ..., "T008"]
}
```

**Valid commands:**
- `/implement` → resolves to T009, T010
- `/implement T009` → valid (in current_tasks)
- `/implement T009 - T010` → valid (both in current_tasks)
- `/implement --help` → shows available tasks and exits

**Invalid commands (should block):**
- `/implement T001` → blocked (already completed)
- `/implement T011` → blocked (not in current_tasks)
- `/implement T009 - T015` → blocked (T011-T015 not in current_tasks)

## Files to Modify

1. `/home/emhar/avaris-ai/.claude/hooks/workflow/handlers/user_prompt.py`
   - Update `is_valid_implement_args()` to validate against current_tasks
   - Add helper method `_parse_task_ids()` to extract task IDs from args
   - Add helper method `_validate_tasks_in_current()` to check tasks exist

2. `/home/emhar/avaris-ai/.claude/hooks/workflow/tests/test_user_prompt_handler.py`
   - Update tests for new validation behavior
   - Add tests for range validation

## Implementation Details

**Step 1: Add helper to parse task IDs from prompt**

```python
def _parse_task_ids(self, prompt: str) -> list[str]:
    """Parse task IDs from /implement command.

    Args:
        prompt: The prompt text

    Returns:
        List of task IDs, empty if no args or invalid format
    """
    cmd = self._triggers.implement.command
    parts = prompt.split()

    # No args case
    if len(parts) == 1 and parts[0] == cmd:
        return []

    # Single task or range
    if len(parts) >= 2 and parts[0] == cmd:
        rest = " ".join(parts[1:])
        # Check for range (T001 - T003)
        range_match = re.match(r"(T\d{3})\s*-\s*(T\d{3})$", rest)
        if range_match:
            start, end = range_match.groups()
            start_num = int(start[1:])
            end_num = int(end[1:])
            if start_num > end_num:
                return []  # Invalid range
            return [f"T{str(i).zfill(3)}" for i in range(start_num, end_num + 1)]
        # Single task
        single_match = re.match(r"T\d{3}$", rest)
        if single_match:
            return [rest]

    return []
```

**Step 2: Add validation against current_tasks**

```python
def _validate_tasks_in_current(self, task_ids: list[str]) -> tuple[bool, str]:
    """Validate task IDs exist in current_tasks.

    Args:
        task_ids: List of task IDs to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not task_ids:
        return True, ""  # No args case, will use defaults

    from release_plan.getters import get_current_tasks_ids  # type: ignore
    current_tasks = get_current_tasks_ids()

    if not current_tasks:
        return False, "No current tasks available"

    invalid_tasks = [t for t in task_ids if t not in current_tasks]
    if invalid_tasks:
        return False, f"Tasks not in current_tasks: {', '.join(invalid_tasks)}. Available: {', '.join(current_tasks)}"

    return True, ""
```

**Step 3: Update `is_valid_implement_args()`**

```python
def is_valid_implement_args(self, prompt: str) -> bool:
    """Validate /implement command arguments.

    Args:
        prompt: The prompt text

    Returns:
        True if valid (no args = default, or task IDs in current_tasks)
    """
    cmd = self._triggers.implement.command
    parts = prompt.split()

    if cmd not in parts:
        return True

    # Command must be first
    if parts[0] != cmd:
        return False

    # No args - valid (defaults to current tasks)
    if len(parts) == 1:
        return True

    # Parse and validate task IDs
    task_ids = self._parse_task_ids(prompt)
    if not task_ids:
        return False  # Invalid format

    is_valid, _ = self._validate_tasks_in_current(task_ids)
    return is_valid
```

**Step 4: Add `--help` flag detection and handler**

```python
def is_help_requested(self, prompt: str) -> bool:
    """Check if --help flag is in prompt.

    Args:
        prompt: The prompt text

    Returns:
        True if --help is requested
    """
    cmd = self._triggers.implement.command
    return f"{cmd} --help" in prompt or f"{cmd} -h" in prompt

def handle_help(self) -> None:
    """Handle /implement --help command."""
    from release_plan.getters import get_current_tasks_ids, get_current_user_story  # type: ignore

    current_tasks = get_current_tasks_ids()
    current_story = get_current_user_story()

    help_text = f"""
/implement - Implement tasks from the current user story

Usage:
  /implement              Implement all current tasks ({', '.join(current_tasks) if current_tasks else 'none'})
  /implement TNNN         Implement a specific task
  /implement TNNN - TNNN  Implement a range of tasks
  /implement --help       Show this help message

Current User Story: {current_story}
Available Tasks: {', '.join(current_tasks) if current_tasks else 'No tasks available'}
"""
    print(help_text)
    sys.exit(0)
```

**Step 5: Update `handle_implement()` to show error message**

```python
def handle_implement(self, prompt: str) -> None:
    """Handle /implement command."""
    task_ids = self._parse_task_ids(prompt)
    is_valid, error_msg = self._validate_tasks_in_current(task_ids)

    if not is_valid:
        print(f"Invalid args: {error_msg}", file=sys.stderr)
        sys.exit(2)

    self._state.activate_workflow()
    # ... rest of validation logic
```

**Step 6: Update `run()` to check help before implement**

In the `run()` method, add help check before implement handling:

```python
# Handle implement help
if self.is_help_requested(prompt):
    self.handle_help()
    return

# Handle implement
if self.is_implement_triggered(prompt):
    self.handle_implement(prompt)
    return
```

**Step 7: Add method to get resolved tasks for downstream use**

```python
def get_resolved_task_ids(self, prompt: str) -> list[str]:
    """Get task IDs to implement.

    Args:
        prompt: The prompt text

    Returns:
        List of task IDs (from args or current state)
    """
    task_ids = self._parse_task_ids(prompt)
    if not task_ids:
        # No args - return all current tasks
        from release_plan.getters import get_current_tasks_ids  # type: ignore
        return get_current_tasks_ids()
    return task_ids
```

## Test Cases

**Note:** Existing tests use `MS-\d{3}` pattern but config uses `T\d{3}`. Will update fixture to use `T\d{3}` for consistency.

**Update fixture in `test_user_prompt_handler.py`:**

```python
@pytest.fixture
def handler():
    """Provide a handler instance with mocked dependencies."""
    with patch("handlers.user_prompt.get_manager") as mock_manager, \
         patch("handlers.user_prompt.get_triggers") as mock_triggers:
        mock_manager.return_value.is_workflow_active.return_value = False
        mock_manager.return_value.is_dry_run_active.return_value = False
        mock_manager.return_value.is_troubleshoot_active.return_value = False
        mock_manager.return_value.activate_workflow = MagicMock()
        mock_manager.return_value.deactivate_workflow = MagicMock()
        mock_manager.return_value.activate_dry_run = MagicMock()
        mock_manager.return_value.reset = MagicMock()
        mock_manager.return_value.reset_deliverables_status = MagicMock()

        # Setup triggers config - use T\d{3} pattern (matching workflow.config.yaml)
        mock_implement = MagicMock()
        mock_implement.command = "/implement"
        mock_implement.arg_pattern = r"T\d{3}(\s*-\s*T\d{3})?$"

        mock_deactivate = MagicMock()
        mock_deactivate.command = "/deactivate-workflow"

        mock_dry_run = MagicMock()
        mock_dry_run.command = "/dry-run"

        mock_troubleshoot = MagicMock()
        mock_troubleshoot.command = "/troubleshoot"

        mock_triggers.return_value.implement = mock_implement
        mock_triggers.return_value.deactivate = mock_deactivate
        mock_triggers.return_value.dry_run = mock_dry_run
        mock_triggers.return_value.troubleshoot = mock_troubleshoot

        yield UserPromptHandler()
```

**Existing tests to UPDATE (change MS-NNN to T-NNN pattern):**

- `TestIsImplementTriggered` - update prompts to use `T001` format
- `TestIsValidImplementArgs` - update to test new validation logic
- `TestHandleImplement` - update pattern and add current_tasks mock
- `TestRun` - update prompts

**New tests to ADD in `test_user_prompt_handler.py`:**

```python
class TestParseTaskIds:
    """Tests for _parse_task_ids method."""

    def test_parse_no_args_returns_empty(self, handler):
        """No args returns empty list."""
        assert handler._parse_task_ids("/implement") == []

    def test_parse_single_task(self, handler):
        """Single task ID parsed correctly."""
        assert handler._parse_task_ids("/implement T009") == ["T009"]

    def test_parse_task_range(self, handler):
        """Task range parsed correctly."""
        assert handler._parse_task_ids("/implement T009 - T011") == ["T009", "T010", "T011"]

    def test_parse_invalid_format_returns_empty(self, handler):
        """Invalid format returns empty list."""
        assert handler._parse_task_ids("/implement invalid") == []
        assert handler._parse_task_ids("/implement T00") == []  # Too short

    def test_parse_reversed_range_returns_empty(self, handler):
        """Reversed range (end < start) returns empty."""
        assert handler._parse_task_ids("/implement T010 - T005") == []


class TestValidateTasksInCurrent:
    """Tests for _validate_tasks_in_current method."""

    def test_empty_list_is_valid(self, handler):
        """Empty list (no args case) is valid."""
        is_valid, msg = handler._validate_tasks_in_current([])
        assert is_valid is True
        assert msg == ""

    def test_valid_task_in_current(self, handler, mocker):
        """Task in current_tasks is valid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        is_valid, msg = handler._validate_tasks_in_current(["T009"])
        assert is_valid is True

    def test_invalid_task_not_in_current(self, handler, mocker):
        """Task not in current_tasks is invalid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        is_valid, msg = handler._validate_tasks_in_current(["T001"])
        assert is_valid is False
        assert "T001" in msg

    def test_partial_range_invalid(self, handler, mocker):
        """Range with some tasks not in current_tasks is invalid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        is_valid, msg = handler._validate_tasks_in_current(["T009", "T010", "T011"])
        assert is_valid is False
        assert "T011" in msg

    def test_no_current_tasks_is_invalid(self, handler, mocker):
        """No current tasks available is invalid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=[]
        )
        is_valid, msg = handler._validate_tasks_in_current(["T009"])
        assert is_valid is False
        assert "No current tasks" in msg


class TestIsValidImplementArgs:
    """Tests for is_valid_implement_args method."""

    def test_no_args_is_valid(self, handler):
        """No arguments is valid (defaults to current tasks)."""
        assert handler.is_valid_implement_args("/implement") is True

    def test_valid_task_is_valid(self, handler, mocker):
        """Valid task in current_tasks is valid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        assert handler.is_valid_implement_args("/implement T009") is True

    def test_valid_range_is_valid(self, handler, mocker):
        """Valid range within current_tasks is valid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        assert handler.is_valid_implement_args("/implement T009 - T010") is True

    def test_invalid_task_is_invalid(self, handler, mocker):
        """Task not in current_tasks is invalid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        assert handler.is_valid_implement_args("/implement T001") is False

    def test_out_of_range_is_invalid(self, handler, mocker):
        """Range extending beyond current_tasks is invalid."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        assert handler.is_valid_implement_args("/implement T009 - T015") is False

    def test_invalid_format_is_invalid(self, handler):
        """Invalid format is invalid."""
        assert handler.is_valid_implement_args("/implement invalid") is False

    def test_non_implement_command_is_valid(self, handler):
        """Non-implement commands pass through."""
        assert handler.is_valid_implement_args("/other-command") is True


class TestIsHelpRequested:
    """Tests for is_help_requested method."""

    def test_help_flag_detected(self, handler):
        """--help flag is detected."""
        assert handler.is_help_requested("/implement --help") is True

    def test_short_help_flag_detected(self, handler):
        """Short -h flag is detected."""
        assert handler.is_help_requested("/implement -h") is True

    def test_no_help_flag(self, handler):
        """No help flag returns False."""
        assert handler.is_help_requested("/implement") is False
        assert handler.is_help_requested("/implement T001") is False


class TestGetResolvedTaskIds:
    """Tests for get_resolved_task_ids method."""

    def test_no_args_returns_current_tasks(self, handler, mocker):
        """No args returns all current tasks."""
        mocker.patch(
            "handlers.user_prompt.get_current_tasks_ids",
            return_value=["T009", "T010"]
        )
        assert handler.get_resolved_task_ids("/implement") == ["T009", "T010"]

    def test_single_task_returns_list(self, handler):
        """Single task returns list with that task."""
        assert handler.get_resolved_task_ids("/implement T009") == ["T009"]

    def test_range_returns_expanded_list(self, handler):
        """Range returns expanded list of tasks."""
        assert handler.get_resolved_task_ids("/implement T009 - T011") == ["T009", "T010", "T011"]
```

## Verification

**Step 1: Run new unit tests**
```bash
cd .claude/hooks/workflow && uv run pytest tests/test_user_prompt_handler.py -v
```

**Step 2: Run regression tests (all workflow tests)**
```bash
cd .claude/hooks/workflow && uv run pytest tests/ -v
```

**Step 3: Manual echo tests**

Test no args (should pass):
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/implement"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 0
```

Test help flag (should print help and exit 0):
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/implement --help"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 0, prints available tasks
```

Test valid task in current_tasks:
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/implement T009"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 0
```

Test out-of-range task (should block):
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/implement T001"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 2 with error message
```

Test invalid format (should block):
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/implement invalid"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 2
```

**Step 4: Regression - Verify existing triggers still work**

Test deactivate still works:
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/deactivate-workflow"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 0
```

Test dry-run still works:
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/dry-run:explore"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Should be 0
```

Test troubleshoot still works (when workflow active):
```bash
echo '{"hook_event_name":"UserPromptSubmit","prompt":"/troubleshoot"}' | python .claude/hooks/workflow/handlers/user_prompt.py
echo $?  # Depends on state
```

## Summary of Changes

**Files to modify:**
1. `.claude/hooks/workflow/handlers/user_prompt.py` - Add 4 new methods, update 2 existing
2. `.claude/hooks/workflow/tests/test_user_prompt_handler.py` - Update fixture, update existing tests, add 6 new test classes

**New methods:**
- `_parse_task_ids()` - Parse task IDs from prompt
- `_validate_tasks_in_current()` - Validate against current_tasks
- `is_help_requested()` - Detect --help flag
- `handle_help()` - Display help with available tasks
- `get_resolved_task_ids()` - Get final task list for downstream

**Updated methods:**
- `is_valid_implement_args()` - Now validates against current_tasks
- `run()` - Add help check before implement handling

## Impact

- **Prevents invalid task implementation**: Can't implement completed or non-existent tasks
- **Clear error messages**: User sees which tasks are available
- **Help flag**: `/implement --help` shows available tasks
- **Backwards compatible**: Valid task IDs still work
- **Uses existing infrastructure**: Leverages `get_current_tasks_ids()` from release_plan
