# Plan: Fix test execution not recorded on non-zero exit (BUG-001)

## Context

E2E test run found a bug: in `write-tests` phase, running `python -m pytest` with exit code 1 (expected in TDD) does not set `tests.executed = true`, so the phase never completes.

**Root cause**: Claude Code fires `PostToolUse` only for **successful** tool calls. When Bash exits non-zero, it fires `PostToolUseFailure` instead. The guardrail system has no `PostToolUseFailure` handler, so the recorder never runs for failed Bash commands.

The recorder's `record_test_execution()` only needs the command string (not exit code), so it works correctly — it just never gets called.

## Fix

### 1. Add `PostToolUseFailure` hook for Bash

**File:** `claudeguard/hooks/hooks.json`

Add a `PostToolUseFailure` entry with `Bash` matcher pointing to a new dispatcher:

```json
"PostToolUseFailure": [
  {
    "matcher": "Bash",
    "hooks": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/dispatchers/post_tool_use_failure.py",
        "timeout": 10
      }
    ]
  }
]
```

### 2. Create `post_tool_use_failure.py` dispatcher

**File:** `claudeguard/scripts/dispatchers/post_tool_use_failure.py`

Thin dispatcher that only records safe operations from failed Bash commands (test execution, deps). Unlike `post_tool_use.py`, it does NOT:
- Parse `tool_result` (PostToolUseFailure has `error` field instead, no `tool_result`)
- Call `Hook.block()` on errors (tool already failed)
- Record PR create or CI check (those require successful JSON output)

```python
def main():
    hook_input = Hook.read_stdin()
    # ... session/workflow guards ...
    config = Config()
    state = StateStore(...)
    recorder = Recorder(state)
    
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")
    phase = state.current_phase
    
    recorder.record_test_execution(phase, command)
    resolve(config, state)
```

## Files to Modify

| Action | Path |
|--------|------|
| Create | `claudeguard/scripts/dispatchers/post_tool_use_failure.py` |
| Modify | `claudeguard/hooks/hooks.json` |

## Verification

- `python3 -m pytest claudeguard/scripts/tests/ -p no:randomly` — all tests pass
- Run `/test-build` E2E — `write-tests` phase should complete after `pytest` with exit code 1
