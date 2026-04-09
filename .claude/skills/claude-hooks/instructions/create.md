## User Prompt

{user_instructions}

## System Instructions

- Make the script executable by running `chmod +x <script_name>.py`
- Use `$CLAUDE_PROJECT_DIR` variable to reference the project directory. Example: `"$CLAUDE_PROJECT_DIR"/.claude/hooks/tests/general_test.py`
- When testing the hook, use `echo` to pipe the hook input if applicable. Example: `echo '{"test": "test"}' | ".claude/hooks/tests/general_test.py"`
- Narrow down the hook with the appropriate matcher if applicable. Example: `matcher: "Skill|Task"`

## Workflow

1. Read @.claude/skills/claude-hooks/references/hooks.md for claude code hooks configuration
2. If `Plan` is specified, enter plan mode by running `EnterPlanMode` command
3. Create the hook script using TDD approach
4. Validate the hook script against the acceptance criteria (See Acceptance Criteria section)
5. Test the hook using `echo` to pipe JSON input if applicable
6. Provide report to main agent

## Constraints

- Do not add unnecessary dependencies — use python standard library where possible
- Do not over-engineer — match the solution complexity to the task complexity
- Do not combine multiple hook behaviors into a single script unless they are tightly related
- Do not hardcode paths — use `$CLAUDE_PROJECT_DIR` for project-relative paths
- Do not skip writing tests — every hook must have at least one passing test before delivery

## Acceptance Criteria

- The hook script is created using TDD approach
- The hook script is tested using `echo` to pipe JSON input if applicable
- Code is written in python
- Solutions are appropriate for the complexity of the task
- Code is robust and resilient to errors
- Hook executes successfully on target event
- Hook handles invalid/malformed input gracefully
- Hook implementation is simple and not complex
- No security vulnerabilities
- Agent frontmatter hooks use the correct nested `hooks:` array structure
