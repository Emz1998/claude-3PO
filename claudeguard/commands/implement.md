---
name: implement
description: Implement a story from the project backlog
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: <story-id> [--tdd] [--skip-explore] [--skip-research] [--reset] [--takeover]
model: haiku
---

Implement story "$0" by following the phased workflow below. Each phase is enforced by hook guardrails — the system will block tool calls that don't match the current phase.

> **Phase = Skill**. To transition between phases, invoke the corresponding `/skill` (e.g. `/explore`, `/research`, `/plan`, etc.). Auto-phases (create-tasks, write-tests, write-code) start automatically — do NOT invoke them as skills.

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' implement ${CLAUDE_SESSION_ID} $ARGUMENTS`

## Story Context

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/github_project/project_manager.py' view $0`

## Instructions

- Follow the phased workflow strictly. The guardrails enforce phase ordering.
- **Phases are skills.** Invoke `/explore`, `/research`, `/plan`, etc. to enter each phase.
- **Auto-phases start automatically** — do NOT invoke `/create-tasks`, `/write-tests`, or `/write-code`.
- All agents must be run in the **foreground** (not background).
- Agent counts must match the limits or the guardrail will block you.
- Only read and write files relevant to the current phase.
- `story_id` is **required** for implement workflow.
- If another session is already active for the same story, the initializer will fail. Use `--reset` to start fresh or `--takeover` to continue where the old session left off.
- Ask questions if unsure. Use `AskUserQuestion`.

## Phases

**Important**: Trigger `/explore` and `/research` in parallel.

### 1. `/explore`

Trigger **3 Explore agents** in parallel:

| Agent     | Focus                                                 |
| --------- | ----------------------------------------------------- |
| Explore 1 | Project structure, configuration, critical files      |
| Explore 2 | Git activity, dependencies, recent changes            |
| Explore 3 | Implementation state, technical health, code patterns |

Allowed: Read, Glob, Grep, Bash (read-only: `ls`, `git status`, `git log`, etc.)

### 2. `/research`

Trigger **2 Research agents** in parallel:

| Agent      | Focus                                   |
| ---------- | --------------------------------------- |
| Research 1 | Web research for solutions              |
| Research 2 | Latest documentation and best practices |

Runs in parallel with `/explore`. Allowed: Read, Glob, Grep, WebFetch, WebSearch.

### 3. `/plan`

1. Invoke the **Plan** agent to design the implementation plan.
2. Consolidate findings from Explore and Research.
3. Read the plan template at `${CLAUDE_PLUGIN_ROOT}/templates/implement-plan.md` and follow it exactly.
4. Write the implementation plan to `.claude/plans/latest-plan.md`.

The plan **must** follow the implement template format (guardrail enforced):

- `## Context` — problem description and motivation
- `## Approach` — implementation strategy and key decisions
- `## Files to Create/Modify` — table with Action and Path columns (guardrail extracts this for write-code file guard)
- `## Verification` — how to verify the implementation

Allowed: Write (only `.claude/plans/latest-plan.md`), Read, Bash (read-only).

### 4. `/plan-review`

1. Invoke the **PlanReview** agent to score the plan.
2. Agent must return `confidence_score` and `quality_score` (1-100).
3. If scores < 80, enters `plan-revision` sub-phase — edit plan and re-invoke PlanReview.
4. Max 3 iterations.
5. Once approved, the workflow **discontinues** for user review.

Allowed: Edit (only `.claude/plans/latest-plan.md`), Read, Glob, Grep.

### 5. create-tasks (AUTO)

> **Auto-phase** — starts automatically after plan-review passes.

1. Fetches project tasks from project_manager for the story.
2. Create Claude tasks (via TaskCreate) for each project task.
3. Each TaskCreate must have `metadata.parent_task_id` and `metadata.parent_task_title`.
4. Phase auto-advances when all project tasks have ≥1 subtask.

### 6. write-tests (AUTO, TDD only)

> **Auto-phase** — starts automatically. Skip if TDD is not enabled.

1. Write failing test files (patterns: `*.test.ts`, `test_*.py`, `*_test.py`, etc.)
2. Run tests to confirm they fail: `pytest`, `npm test`, `jest`, etc.

Allowed: Write (test files only), Bash (test commands only).

### 7. `/tests-review`

1. Invoke the **TestReviewer** agent.
2. Agent must return verdict: `Pass` or `Fail`.
3. If `Fail`, enters revision sub-phase — edit tests and re-invoke.

Allowed: Edit (only test files written this session), Read, Glob, Grep.

### 8. write-code (AUTO)

> **Auto-phase** — starts automatically after tests-review (TDD) or create-tasks (non-TDD).

1. Write implementation code — **only files listed in `## Files to Create/Modify`** (guardrail enforced).
2. Run tests to verify.

Allowed: Write (only listed files), Edit, Read, Glob, Grep, Bash (test commands only).

### 9. `/validate`

1. Invoke the **QASpecialist** agent.
2. If result is `Fail`, go back to write-code and iterate.
3. If `Pass`, proceed.

Allowed: Read, Glob, Grep, Bash (test commands).

### 10. `/code-review`

1. Invoke the **CodeReviewer** agent.
2. Agent must return `confidence_score` and `quality_score` (1-100).
3. If scores < 90, enters revision sub-phase — edit code and re-invoke.
4. Max 3 iterations.

Allowed: Edit (only code files written this session), Read, Glob, Grep.

### 11. `/pr-create`

1. Stage, commit, and push changes.
2. Create PR: `gh pr create --json number`
3. `--json` flag is **required** — guardrail blocks without it.

Allowed: Bash (`git push`, `git commit`, `git add`, `gh pr create`).

### 12. `/ci-check`

1. Check CI: `gh pr checks --json name,conclusion`
2. `--json` flag is **required**.
3. If CI fails, go back to write-code and iterate.

Allowed: Bash (`gh pr checks`, `gh pr status`).

### 13. `/write-report`

1. Write report to `.claude/reports/report.md`.
2. Include frontmatter: `timestamp`, `date`, `story_implemented`, `pr_number`, `branch_name`.
3. Present the report to the user before stopping.

Allowed: Write (only `.claude/reports/`), Read.

## Rules

- Follow phase order strictly. Guardrails enforce it.
- Do not skip phases unless in the `skip` list.
- Do not invoke auto-phases as skills.
- Do not invoke agents beyond their max count.
- Do not stop until all phases are completed — the stop hook will block you.
- Validate work through tests, not assumptions.

## References

- **Plan template**: `${CLAUDE_PLUGIN_ROOT}/templates/implement-plan.md`
- **Plan**: `.claude/plans/latest-plan.md`
- **Report**: `.claude/reports/report.md`
