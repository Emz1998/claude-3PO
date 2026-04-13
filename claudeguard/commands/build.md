---
name: build
description: Build a feature from free-text instructions
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: <instructions> [--tdd] [--skip-explore] [--skip-research]
model: haiku
---

Build the coding task "$1" by following the phased workflow below. Each phase is enforced by hook guardrails — the system will block tool calls that don't match the current phase.

> **Phase = Skill**. To transition between phases, invoke the corresponding `/skill` (e.g. `/explore`, `/research`, `/plan`, etc.). Auto-phases (write-tests, write-code) start automatically — do NOT invoke them as skills.

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' build ${CLAUDE_SESSION_ID} $ARGUMENTS`

## Instructions

- Follow the phased workflow strictly. The guardrails enforce phase ordering.
- **Phases are skills.** Invoke `/explore`, `/research`, `/plan`, etc. to enter each phase.
- **Auto-phases start automatically** — do NOT invoke `/write-tests` or `/write-code`.
- All agents must be run in the **foreground** (not background).
- Agent counts must match the limits or the guardrail will block you.
- Only read and write files relevant to the current phase.
- Ask questions if unsure. Use `AskUserQuestion`.

## Phases

**Important**: Trigger `/explore` and `/research` in parallel.
**Important**: `Explore` and `Research` agents must run in parallel (Total of 5 agents in parallel).

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

1. Consolidate findings from Explore and Research into `CODEBASE.md`.
2. Invoke the **Plan** agent to design the implementation plan.
3. Read the plan template at `${CLAUDE_PLUGIN_ROOT}/templates/plan.md` and follow it exactly.
4. Write the implementation plan to `.claude/plans/latest-plan.md`.
5. Write the contracts specification to `.claude/contracts/latest-contracts.md`.

The plan **must** follow the template format (guardrail enforced):

- `## Dependencies` — bullet list of packages (`- package-name`). No ### subsections.
- `## Contracts` — bullet list of contract names (`- ContractName`). No ### subsections.
- `## Tasks` — bullet list of task subjects (`- Task subject`). No ### subsections. Each bullet becomes a planned task validated by the TaskCreated hook.

Allowed: Write (only `.claude/plans/latest-plan.md` and `.claude/contracts/latest-contracts.md`), Read, Bash (read-only).

### 4. `/plan-review`

1. Invoke the **PlanReview** agent to score the plan.
2. Agent must return `confidence_score` and `quality_score` (1-100).
3. If scores < 80, enters `plan-revision` sub-phase — edit plan and re-invoke PlanReview.
4. Max 3 iterations.
5. Edits must not remove `## Dependencies`, `## Contracts`, or `## Tasks` sections (guardrail enforced).
6. Once approved, the workflow **discontinues** for user review.

Allowed: Edit (only `.claude/plans/latest-plan.md`), Read, Glob, Grep.

### 5. `/install-deps`

1. Read the plan's `## Dependencies` section.
2. Write dependencies to the package manager file (`package.json`, `requirements.txt`, `go.mod`, etc.)
3. Run the install command (`npm install`, `pip install -r requirements.txt`, etc.)
4. Phase completes when install command runs successfully.

Allowed: Write (package manager files only), Bash (install commands only).

### 6. `/define-contracts`

1. Read `.claude/contracts/latest-contracts.md` (written during plan phase).
2. Write actual code files (interfaces, types, stubs) that implement the contracts.
3. Guardrail validates all contract names from contracts.md appear in written code.
4. Phase completes when all contracts are found in code.

Allowed: Write (code files only), Read, Glob, Grep.

### 7. write-tests (AUTO, TDD only)

> **Auto-phase** — starts automatically after define-contracts. Skip if TDD is not enabled.

1. Write failing test files (patterns: `*.test.ts`, `test_*.py`, `*_test.py`, etc.)
2. Run tests to confirm they fail: `pytest`, `npm test`, `jest`, etc.

Allowed: Write (test files only), Bash (test commands only).

### 8. `/test-review` (TDD only)

1. Invoke the **TestReviewer** agent.
2. Agent must return verdict: `Pass` or `Fail`.
3. If `Fail`, enters `refactor` sub-phase — edit tests and re-invoke.

Allowed: Edit (only test files written this session), Read, Glob, Grep.

### 9. write-code (AUTO)

> **Auto-phase** — starts automatically after test-review (TDD) or define-contracts (non-TDD).

1. Write implementation code to pass tests (or implement plan directly if no TDD).
2. Run tests to verify.

Allowed: Write (code files only), Edit, Read, Glob, Grep, Bash (test commands only).

### 10. `/quality-check`

1. Invoke the **QASpecialist** agent.
2. If result is `Fail`, go back to write-code and iterate.
3. If `Pass`, proceed.

Allowed: Read, Glob, Grep, Bash (test commands).

### 11. `/code-review`

1. Invoke the **CodeReviewer** agent.
2. Agent must return `confidence_score` and `quality_score` (1-100).
3. If scores < 90, enters `refactor` sub-phase — edit code and re-invoke.
4. Max 3 iterations.

Allowed: Edit (only code files written this session), Read, Glob, Grep.

### 12. `/pr-create`

1. Stage, commit, and push changes.
2. Create PR: `gh pr create --json number`
3. `--json` flag is **required** — guardrail blocks without it.

Allowed: Bash (`git push`, `git commit`, `git add`, `gh pr create`).

### 13. `/ci-check`

1. Check CI: `gh pr checks --json name,conclusion`
2. `--json` flag is **required**.
3. If CI fails, go back to write-code and iterate.

Allowed: Bash (`gh pr checks`, `gh pr status`).

### 14. `/write-report`

1. Write report to `.claude/reports/report.md`.
2. Include frontmatter: `timestamp`, `date`, `task_description`, `pr_number`, `branch_name`.
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

- **Plan template**: `${CLAUDE_PLUGIN_ROOT}/templates/plan.md`
- **Plan**: `.claude/plans/latest-plan.md`
- **Contracts**: `.claude/contracts/latest-contracts.md`
- **Report**: `.claude/reports/report.md`
