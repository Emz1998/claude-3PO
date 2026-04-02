# Plan: Create `reminder.py` — Phase-Aware Context Injection

## Context

The workflow hooks system at `.claude/hooks/workflow/` enforces a multi-phase development workflow with guards (validate/block) and recorders (mutate state). However, it **never injects contextual reminders** — Claude doesn't know what phase it's in, what agents are allowed, what files to modify, or what to do next. The only context injection today is `_handle_exit_plan_mode_pre()` in guardrail.py which returns plan content as `additionalContext`.

This creates a gap: Claude must rely on the command prompt alone to know the workflow, and often gets confused about what phase it's in or what to do next after a subagent completes.

## Approach

Create a `reminder.py` module that generates phase-specific `additionalContext` strings, integrated into the existing dispatchers at two high-value injection points:

1. **PostToolUse** — After a tool completes, inject phase context reminders (current phase, what's next)
2. **SubagentStop** — After an agent completes and phase transitions, inject transition + failure reminders
3. **SubagentStart** (new dispatcher) — Inject agent-role instructions directly into the subagent's context

**Separation of concerns:**
- PreToolUse = guardrail only (validation/blocking) — no reminders here
- PostToolUse = phase context reminders (after tool executes)
- SubagentStart = agent role reminders (into the subagent)
- SubagentStop = phase transition + failure reminders

The module is **read-only on state** (no mutations), keeping the separation: guards validate, recorder mutates, reminder injects context.

## Steps

### Step 1: Create `reminder.py`

Create `/home/emhar/avaris-ai/.claude/hooks/workflow/reminder.py` with:

- `PHASE_REMINDERS` dict mapping each phase to a concise context template string
- `AGENT_REMINDERS` dict mapping agent types to role-specific instructions
- `get_post_tool_reminder(hook_input, store) -> str | None` — for PostToolUse events, returns phase context after tool completes
- `get_agent_start_reminder(hook_input, store) -> str | None` — for SubagentStart events, returns agent-role instructions injected into the subagent
- `get_phase_transition_reminder(hook_input, store) -> str | None` — for SubagentStop events, reads the NEW phase (after recorder has already advanced it) and returns next-action + failure guidance

Key design: reminder reads state AFTER guardrail.py subprocess completes, so it sees the post-transition phase.

#### Phase Context Reminders (PostToolUse Agent)

| Phase | Reminder |
|-------|----------|
| `explore` | "Phase: EXPLORE. Launch 3 Explore + 2 Research agents in parallel. All must complete before moving to plan phase." |
| `plan` | "Phase: PLAN. Synthesize exploration findings into a concrete implementation plan." |
| `review` | "Phase: REVIEW. Plan review iteration {N}/3. Scores must be >= 80/80 to approve." |
| `write-tests` | "Phase: WRITE-TESTS (TDD). Write failing tests, then launch TestReviewer. Only test files allowed." |
| `write-code` | "Phase: WRITE-CODE. Files from plan: {list}. When done, launch Validator agent." |
| `validate` | "Phase: VALIDATE. If Pass → pr-create. If Fail → back to write-code." |

#### Agent Role Reminders (SubagentStart — injected into subagent's context)

| Agent Type | Reminder |
|------------|----------|
| `Explore` | "Focus on codebase structure, existing patterns, and relevant files." |
| `Research` | "Research external docs, best practices, and patterns for the task." |
| `Plan` | "Synthesize explore/research findings into a plan with steps and file changes." |
| `PlanReview` | "Score confidence (0-100) and quality (0-100). End response with: confidence: NN, quality: NN" |
| `TestReviewer` | "Review test coverage and quality. End response with exactly 'Pass' or 'Fail'." |
| `Validator` | "Verify implementation passes tests and matches plan. End with 'Pass' or 'Fail'." |

#### Phase Transition Reminders (SubagentStop — after phase advances)

| New Phase | Reminder |
|-----------|----------|
| `plan` | "All exploration complete. Launch a Plan agent to design the implementation." |
| `write-plan` | "Plan formulated. Write it to .claude/plans/ with required sections: Context, Approach/Steps, Files to Modify, Verification." |
| `approved` | "Plan review passed. Use ExitPlanMode to present the plan to the user for approval." |
| `write-tests` | "Tasks created. TDD mode: write failing tests first." |
| `write-code` | "Tests reviewed. Write minimal code to pass them. Plan files: {list}." |
| `pr-create` | "Validation passed. Create PR with gh pr create." |
| `ci-check` | "PR created. Run gh pr checks to verify CI." |
| `report` | "CI passed. Write completion report to .claude/reports/latest-report.md." |

#### PostToolUse ExitPlanMode Reminder (after user approves plan)

When ExitPlanMode PostToolUse fires, the recorder advances phase from "approved" to the next coding phase. The reminder should tell Claude what phase it's now in:

| Next Phase | Reminder |
|------------|----------|
| `task-create` | "User approved the plan. Create tasks matching the story context using TaskManager agent." |
| `write-tests` | "User approved the plan. TDD mode: write failing tests first." |
| `write-code` | "User approved the plan. Begin implementation. Plan files: {list}." |

#### Failure/Regression Reminders (SubagentStop — when scores fail or phase regresses)

| Scenario | Reminder |
|----------|----------|
| PlanReview scores < 80/80 | "Plan review FAILED. Scores: confidence={N}, quality={N} (threshold: 80/80). Iteration {N}/3. Revise the plan and launch PlanReview again." |
| PlanReview max iterations | "Plan review reached max iterations (3). Scores: confidence={N}, quality={N}. Workflow failed — ask the user for guidance." |
| TestReviewer Fail | "Test review FAILED. Revise test files and launch TestReviewer again." |
| Validator Fail | "Validation FAILED. Returning to write-code phase. Fix the implementation and re-validate." |

### Step 2: Modify `post_tool_use.py` dispatcher

Update `/home/emhar/avaris-ai/.claude/hooks/workflow/dispatchers/post_tool_use.py`:

- Import `reminder.get_post_tool_reminder` and `StateStore`
- After guardrail decision, call `get_post_tool_reminder()`
- If reminder returns context, output as `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}`
- If guardrail returned JSON (ExitPlanMode), merge reminder into existing additionalContext
- If no reminder, keep current behavior

### Step 3: Create `subagent_start.py` dispatcher

Create new `/home/emhar/avaris-ai/.claude/hooks/workflow/dispatchers/subagent_start.py`:

- Import `reminder.get_agent_start_reminder` and `StateStore`
- Read stdin, call `get_agent_start_reminder()`
- If reminder returns context, output as `{"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": "..."}}`
- Register in `.claude/settings.json` under `SubagentStart` hook event

### Step 4: Modify `subagent_stop.py` dispatcher

Update `/home/emhar/avaris-ai/.claude/hooks/workflow/dispatchers/subagent_stop.py`:

- Import `reminder.get_phase_transition_reminder` and `StateStore`
- After guardrail decision (which runs recorder → advances phase), call `get_phase_transition_reminder()`
- If reminder returns context, output as `{"hookSpecificOutput": {"hookEventName": "SubagentStop", "additionalContext": "..."}}`
- If no reminder, keep current behavior (exit 0)

### Step 5: Write tests

Create `/home/emhar/avaris-ai/.claude/hooks/workflow/tests/test_reminder.py`:

- Test each phase produces expected reminder content
- Test no reminder when `workflow_active` is false
- Test agent-specific reminders for each agent type
- Test phase transition reminders after recorder advances state
- Follow existing test patterns (tmp_path fixtures, `StateStore(tmp/state.json)`)

### Step 6: Validate with dry run

Run existing dry runs to ensure no regressions, then manually test reminder output with echo piping.

## Files to Modify

| File | Action |
|------|--------|
| `.claude/hooks/workflow/reminder.py` | Create — core reminder module |
| `.claude/hooks/workflow/dispatchers/post_tool_use.py` | Edit — add reminder injection after guardrail |
| `.claude/hooks/workflow/dispatchers/subagent_start.py` | Create — new dispatcher for agent-role reminders |
| `.claude/hooks/workflow/dispatchers/subagent_stop.py` | Edit — add reminder injection after guardrail |
| `.claude/settings.json` | Edit — register SubagentStart hook |
| `.claude/hooks/workflow/tests/test_reminder.py` | Create — unit tests |

## Verification

1. Run `pytest .claude/hooks/workflow/tests/test_reminder.py -v` to verify unit tests pass
2. Run existing tests `pytest .claude/hooks/workflow/tests/ -v` to verify no regressions
3. Test dispatcher integration with echo piping:
   ```bash
   echo '{"hook_event_name":"PreToolUse","tool_name":"Agent","tool_input":{"subagent_type":"Explore","description":"x","prompt":"x"},"tool_use_id":"t1","session_id":"s","transcript_path":"t","cwd":".","permission_mode":"default"}' | python3 .claude/hooks/workflow/dispatchers/pre_tool_use.py
   ```
4. Run existing dry runs to check no regressions:
   ```bash
   python3 .claude/hooks/workflow/dry_runs/plan_dry_run.py
   ```
