## User Prompt

{user_instructions}

## System Instructions

- Use `$CLAUDE_PROJECT_DIR` variable to reference the project directory. Example: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/tests/general_test.py`
- When testing the script, use `echo` to pipe input if applicable. Example: `echo '{"test": "test"}' | ".claude/hooks/tests/general_test.py"`
- Preserve existing behavior unless the task explicitly asks to change it
- Keep scripts executable after refactoring (`chmod +x` if needed)

## Workflow

1. Read the existing script and understand its current behavior, inputs, and outputs
2. Identify existing tests. If none exist, write tests that capture current behavior before refactoring
3. If `Plan` is specified, enter plan mode by running `EnterPlanMode` command
4. Refactor the script incrementally, running tests after each change
5. Validate refactored script against the acceptance criteria (See Acceptance Criteria section)
6. Test the script end-to-end using `echo` to pipe JSON input if applicable
7. Provide report to main agent

## Constraints

- Do not change the script's public interface (CLI args, stdin format, stdout/stderr format) unless the task requires it
- Do not add new dependencies unless justified by the refactoring goal
- Do not combine refactoring with feature changes in the same pass — refactor first, then add features
- Do not delete or skip existing tests — fix them if they break due to refactoring
- Do not over-abstract — extract helpers only when there is clear duplication or readability gain

## Acceptance Criteria

- Existing behavior is preserved unless explicitly changed by the task
- Existing tests pass after refactoring (no regressions)
- New tests are added if refactoring introduces new code paths
- Code is written in python
- Solutions are appropriate for the complexity of the task
- Code is robust and resilient to errors
- Script executes successfully on target event
- Script handles invalid/malformed input gracefully
- Implementation is simple and not complex
- No security vulnerabilities
