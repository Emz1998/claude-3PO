## User Instructions

{user_instructions}

## Instructions

- Use `$CLAUDE_PROJECT_DIR` variable to reference the project directory. Example: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/tests/general_test.py`
- When reproducing the issue, use `echo` to pipe the hook input if applicable. Example: `echo '{"test": "test"}' | ".claude/hooks/tests/general_test.py"`
- Run the script directly in the terminal to observe raw output, exit codes, and stderr
- Check the hook's log file if one exists for recent errors or stack traces

## Workflow

1. Reproduce the issue by running the script directly with sample input
2. Check exit code (`echo $?`) and stderr output to classify the failure
3. Read the script source to understand the expected behavior
4. Identify the root cause — narrow down to the specific line or condition
5. If `Plan` is specified, enter plan mode by running `EnterPlanMode` command
6. Fix the issue using TDD approach — write a test that reproduces the bug, then fix
7. Verify the fix by running the script end-to-end with the original failing input
8. Run all existing tests to confirm no regressions
9. Provide report to main agent

## Constraints

- Do not change unrelated code while fixing a bug — keep the diff minimal
- Do not suppress errors or swallow exceptions to make the script "pass"
- Do not skip reproducing the issue first — always confirm the failure before fixing
- Do not remove or weaken existing tests to make them pass after a fix
- Do not add workarounds without documenting why — prefer proper fixes over hacks

## Acceptance Criteria

- Root cause is identified and documented in the report
- A test exists that reproduces the original failure
- The fix addresses the root cause, not just the symptom
- All existing tests pass after the fix (no regressions)
- Script executes successfully with the originally failing input
- Code is written in python
- Script handles invalid/malformed input gracefully
- No security vulnerabilities introduced by the fix
