## Context

The workflow guardrail block messages are terse -- they state what went wrong but don't consistently explain **why** or **what to do next**. This makes debugging workflow blocks harder than necessary. The goal is to improve every block message to follow a consistent pattern: `"Blocked: <what>. <why/next action>."` -- concise but actionable.

## Approach

Pure string literal refactor across guardrail.py and all guard modules. No function signatures, control flow, or architectural changes. One minor code tweak in read_guard.py to include `{phase}` in the message (variable already in scope).

## Files to Modify

- `.claude/hooks/workflow/guardrail.py` — 5 block messages in `_handle_exit_plan_mode_pre()`
- `.claude/hooks/workflow/guards/agent_guard.py` — ~18 block messages across phase checks
- `.claude/hooks/workflow/guards/write_guard.py` — 7 block messages across phase checks
- `.claude/hooks/workflow/guards/stop_guard.py` — 3 block messages
- `.claude/hooks/workflow/guards/read_guard.py` — 1 block message (add phase to f-string)
- `.claude/hooks/workflow/guards/webfetch_guard.py` — 1 block message
- `.claude/hooks/workflow/guards/bash_guard.py` — 2 block messages
- `.claude/hooks/workflow/guards/task_guard.py` — 1 block message

## Steps

1. Update `guardrail.py` — improve 5 ExitPlanMode block messages
2. Update `agent_guard.py` — improve all ~18 agent block messages  
3. Update `write_guard.py` — improve 7 write block messages
4. Update `stop_guard.py` — improve 3 stop block messages
5. Update `read_guard.py` — add phase to the 1 block message
6. Update `webfetch_guard.py` — improve 1 domain block message
7. Update `bash_guard.py` — improve 2 PR block messages
8. Update `task_guard.py` — improve 1 task naming block message
9. Update any tests that assert on exact block message strings

## Message Pattern

Every message: `"Blocked: <what happened>. <actionable next step>."`

Example improvements:
- Before: `"No written plan recorded. Write the plan to .claude/plans/ first."`
- After: `"Blocked: ExitPlanMode requires a written plan. Write your plan to .claude/plans/ before exiting plan mode."`

- Before: `"Agent 'Research' not allowed in phase 'plan'. Allowed: Plan"`
- After: `"Blocked: 'Research' agent is not allowed during 'plan' phase. Only the Plan agent may run now -- launch a Plan agent to proceed."`

- Before: `"Cannot create PR before validation passes"`
- After: `"Blocked: Cannot create PR -- validation has not passed yet. Run the Validator agent to get a 'Pass' result before creating the PR."`

## Verification

1. Run existing tests: `cd .claude/hooks/workflow && python -m pytest tests/ -v`
2. Test guardrail manually with sample hook inputs:
   ```bash
   echo '{"hook_event_name":"PreToolUse","tool_name":"ExitPlanMode"}' | python3 .claude/hooks/workflow/guardrail.py --hook-input '...' --reason
   ```
3. Verify no imports or function signatures changed
4. Grep for old message fragments to ensure all were updated
