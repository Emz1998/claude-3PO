---
name: implement
description: Implement the task
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: <task-to-implement>
model: haiku
hooks:
  PreToolUse:
    - hooks:
        - type: command
          command: ./scripts/pre_tool_use.py
          timeout: 10
  PostToolUse:
    - hooks:
        - type: command
          command: ./scripts/post_tool_use.py
          timeout: 10
  Stop:
    - hooks:
        - type: command
          command: ./scripts/stop.py
          timeout: 10
---

Implement the coding task "$1" by following the phased workflow below. Each phase is enforced by hook guardrails — the system will block tool calls that don't match the current phase.

> **Phase = Skill**. To transition between phases, invoke the corresponding `/skill` (e.g. `/explore`, `/research`, `/plan`, etc.). The guardrails track the current phase via skill invocations.

## Workflow Initialization

!`python3 scripts/utils/initializer.py implement ${CLAUDE_SESSION_ID} $ARGUMENTS`

## Story Context

!`python3 github_project/project_manager.py view $0`

## Instructions

- Follow the phased workflow strictly. The guardrails enforce phase ordering.
- **Phases are skills.** Invoke `/explore`, `/research`, `/plan`, etc. to enter each phase.
- All agents must be run in the **foreground** (not background).
- Agent counts must match the limits or the guardrail will block you.
- Only read and write files relevant to the current phase.
- Ask questions if unsure. Use `AskUserQuestion`.

## Phases

### 1. `/explore`

Trigger **3 Explore agents** in parallel:

| Agent | Focus |
|---|---|
| Explore 1 | Project structure, configuration, critical files |
| Explore 2 | Git activity, dependencies, recent changes |
| Explore 3 | Implementation state, technical health, code patterns |

Allowed: Read, Glob, Grep, Bash (read-only: `ls`, `git status`, `git log`, etc.)

### 2. `/research`

Trigger **2 Research agents** in parallel:

| Agent | Focus |
|---|---|
| Research 1 | Web research for solutions |
| Research 2 | Latest documentation and best practices |

Runs in parallel with `/explore`. Allowed: Read, Glob, Grep, WebFetch, WebSearch.

### 3. `/plan`

1. Consolidate findings from Explore and Research into `CODEBASE.md`.
2. Write the implementation plan to `.claude/plans/plan.md`.

Allowed: Write (only `.claude/plans/plan.md`), Read, Bash (read-only).

### 4. `/plan-review`

1. Invoke the **PlanReview** agent to score the plan.
2. Agent must return `confidence_score` and `quality_score` (1-100).
3. If scores < 90, enters `plan-revision` sub-phase — edit plan and re-invoke PlanReview.
4. Max 3 iterations.
5. Once approved, present the plan to the user.

Allowed: Edit (only `.claude/plans/plan.md`), Read, Glob, Grep.

### 5. `/write-tests` (TDD only)

> Skip if TDD is not enabled.

1. Write failing test files (patterns: `*.test.ts`, `test_*.py`, `*_test.py`, etc.)
2. Run tests to confirm they fail: `pytest`, `npm test`, `jest`, etc.

Allowed: Write (test files only), Bash (test commands only).

### 6. `/test-review` (TDD only)

1. Invoke the **TestReviewer** agent.
2. Agent must return verdict: `Pass` or `Fail`.
3. If `Fail`, enters `refactor` sub-phase — edit tests and re-invoke.

Allowed: Edit (only test files written this session), Read, Glob, Grep.

### 7. `/write-code`

1. Write implementation code to pass tests (or implement plan directly if no TDD).
2. Run tests to verify.

Allowed: Write (code files only), Edit, Read, Glob, Grep, Bash (test commands only).

### 8. `/quality-check`

1. Invoke the **QASpecialist** agent.
2. If result is `Fail`, go back to `/write-code` and iterate.
3. If `Pass`, proceed.

Allowed: Read, Glob, Grep, Bash (test commands).

### 9. `/code-review`

1. Invoke the **CodeReviewer** agent.
2. Agent must return `confidence_score` and `quality_score` (1-100).
3. If scores < 90, enters `refactor` sub-phase — edit code and re-invoke.
4. Max 3 iterations.

Allowed: Edit (only code files written this session), Read, Glob, Grep.

### 10. `/pr-create`

1. Stage, commit, and push changes.
2. Create PR: `gh pr create --json number`
3. `--json` flag is **required** — guardrail blocks without it.

Allowed: Bash (`git push`, `git commit`, `git add`, `gh pr create`).

### 11. `/ci-check`

1. Check CI: `gh pr checks --json name,conclusion`
2. `--json` flag is **required**.
3. If CI fails, go back to `/write-code` and iterate.

Allowed: Bash (`gh pr checks`, `gh pr status`).

### 12. `/write-report`

1. Write report to `.claude/reports/latest-report.md`.
2. Archive previous report to `.claude/reports/archive/`.
3. Include frontmatter: `timestamp`, `date`, `story_implemented`, `pr_number`, `branch_name`, `sprint_number`.
4. Present the report to the user before stopping.

Allowed: Write (only `.claude/reports/`), Read.

## Rules

- Follow phase order strictly. Guardrails enforce it.
- Do not skip phases unless in the `skip` list.
- Do not invoke agents beyond their max count.
- Do not stop until all phases are completed — the stop hook will block you.
- Validate work through tests, not assumptions.

## References

- **Plan**: `.claude/plans/plan.md`
- **Report**: `.claude/reports/latest-report.md`
- **Archive**: `.claude/reports/archive/`
