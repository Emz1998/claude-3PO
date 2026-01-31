---
name: dry-run-workflow
description: Dry run the /implement workflow to test guardrail enforcement
argument-hint: <milestone-id> [tdd|ta|default]
model: opus
---

## Instructions

- This is a **test run** for the /implement workflow guardrail
- Do NOT perform any actual implementation work
- Subagents should exit immediately without doing work
- Verify guardrail blocks out-of-order subagent calls
- Make sure to trigger the subagents. Instruct it to exit right away and to not perform any work.
- No test commands
- Do not use echo to test command execution
- If you need help, stop and ask user for help
- **DO NOT** manually change the cache unless we are **resetting** the cache. If subagent cache didn't transition, exit and ask user for help.

## Workflow Test Sequence

### Phase 1: Pre-Coding (Common to All Modes)

1. **Initialize Cache**
   - Ensure `.claude/hooks/cache.json` exists
   - Set `implement_workflow_active` to `true`
   - Set `implement_workflow_state` to `IMPLEMENT_ACTIVE`

2. **Test Pre-Coding Transitions** (run sequentially)
   - Read a todo file from `project/{version}/{phase}/{milestone}/todos/` → transitions to `TODO_READ`
   - Invoke `codebase-explorer` (should pass) → transitions to `EXPLORER_DONE`
   - Invoke `planning-specialist` (should pass) → transitions to `PLANNER_DONE`
   - Invoke `plan-consultant` (should pass) → transitions to `CONSULTANT_DONE`

### Phase 2: Coding Workflow (Choose One Mode)

#### Option A: TDD Mode (5 steps)

Set `implement_coding_mode` to `tdd` before starting coding phase.

| Step | State          | Allowed Subagent(s)                                            | Action                  |
| ---- | -------------- | -------------------------------------------------------------- | ----------------------- |
| 1    | `CODING_TDD_1` | `test-engineer`                                                | Create failing tests    |
| 2    | `CODING_TDD_2` | `version-manager`                                              | Commit tests            |
| 3    | `CODING_TDD_3` | `frontend-engineer`, `backend-engineer`, `fullstack-developer` | Implement to pass tests |
| 4    | `CODING_TDD_4` | `code-reviewer`                                                | Review and iterate      |
| 5    | `CODING_TDD_5` | `version-manager`                                              | Final commit            |

#### Option B: TA Mode (Tests After, 4 steps)

Set `implement_coding_mode` to `ta` before starting coding phase.

| Step | State         | Allowed Subagent(s)                                            | Action         |
| ---- | ------------- | -------------------------------------------------------------- | -------------- |
| 1    | `CODING_TA_1` | `frontend-engineer`, `backend-engineer`, `fullstack-developer` | Implement code |
| 2    | `CODING_TA_2` | `test-engineer`                                                | Create tests   |
| 3    | `CODING_TA_3` | `code-reviewer`                                                | Review         |
| 4    | `CODING_TA_4` | `version-manager`                                              | Commit         |

#### Option C: Default Mode (3 steps)

Set `implement_coding_mode` to `default` before starting coding phase.

| Step | State              | Allowed Subagent(s)                                            | Action         |
| ---- | ------------------ | -------------------------------------------------------------- | -------------- |
| 1    | `CODING_DEFAULT_1` | `frontend-engineer`, `backend-engineer`, `fullstack-developer` | Implement code |
| 2    | `CODING_DEFAULT_2` | `code-reviewer`                                                | Review         |
| 3    | `CODING_DEFAULT_3` | `version-manager`                                              | Commit         |

### Phase 3: Test Guardrail Blocking

For each test, manually set the cache state, then invoke the blocked subagent.

**Pre-Coding Blocking Tests:**

| State           | Test Subagent         | Expected Result | Allowed Subagent      |
| --------------- | --------------------- | --------------- | --------------------- |
| `TODO_READ`     | `planning-specialist` | BLOCKED         | `codebase-explorer`   |
| `EXPLORER_DONE` | `plan-consultant`     | BLOCKED         | `planning-specialist` |
| `PLANNER_DONE`  | `code-reviewer`       | BLOCKED         | `plan-consultant`     |

**TDD Mode Blocking Tests:**

| State          | Test Subagent       | Expected Result | Allowed Subagent(s)                                            |
| -------------- | ------------------- | --------------- | -------------------------------------------------------------- |
| `CODING_TDD_1` | `frontend-engineer` | BLOCKED         | `test-engineer`                                                |
| `CODING_TDD_2` | `code-reviewer`     | BLOCKED         | `version-manager`                                              |
| `CODING_TDD_3` | `test-engineer`     | BLOCKED         | `frontend-engineer`, `backend-engineer`, `fullstack-developer` |

**TA Mode Blocking Tests:**

| State         | Test Subagent     | Expected Result | Allowed Subagent(s)                                            |
| ------------- | ----------------- | --------------- | -------------------------------------------------------------- |
| `CODING_TA_1` | `test-engineer`   | BLOCKED         | `frontend-engineer`, `backend-engineer`, `fullstack-developer` |
| `CODING_TA_2` | `code-reviewer`   | BLOCKED         | `test-engineer`                                                |
| `CODING_TA_3` | `version-manager` | BLOCKED         | `code-reviewer`                                                |

**Default Mode Blocking Tests:**

| State              | Test Subagent     | Expected Result | Allowed Subagent(s)                                            |
| ------------------ | ----------------- | --------------- | -------------------------------------------------------------- |
| `CODING_DEFAULT_1` | `test-engineer`   | BLOCKED         | `frontend-engineer`, `backend-engineer`, `fullstack-developer` |
| `CODING_DEFAULT_2` | `version-manager` | BLOCKED         | `code-reviewer`                                                |
| `CODING_DEFAULT_3` | `code-reviewer`   | BLOCKED         | `version-manager`                                              |

**Test Sequence:**

1. Set cache to `TODO_READ` state
   - Try `planning-specialist` → should be blocked (only `codebase-explorer` allowed)

2. Set cache to `EXPLORER_DONE` state
   - Try `plan-consultant` → should be blocked (only `planning-specialist` allowed)

3. Set cache to `PLANNER_DONE` state
   - Try `code-reviewer` → should be blocked (only `plan-consultant` allowed)

4. Set cache to coding state (based on mode selected in Phase 2)
   - Test blocked subagent for that state per tables above

### Phase 4: Cleanup

- Set `implement_workflow_active` to `false`
- Set `implement_workflow_state` to `IDLE`
- Clear `implement_coding_mode` and `implement_coding_step`

## Expected Results Summary

### Pre-Coding Phase

| State             | Allowed Subagent    | Blocked Subagents |
| ----------------- | ------------------- | ----------------- |
| `TODO_READ`       | codebase-explorer   | All others        |
| `EXPLORER_DONE`   | planning-specialist | All others        |
| `PLANNER_DONE`    | plan-consultant     | All others        |
| `CONSULTANT_DONE` | (transition only)   | All subagents     |

### Coding Phase (per mode)

**TDD Mode:**

- Enforces test-first: tests → commit → implement → review → commit
- 5 discrete states with strict ordering

**TA Mode:**

- Enforces implement-then-test: implement → tests → review → commit
- 4 discrete states with strict ordering

**Default Mode:**

- Minimal workflow: implement → review → commit
- 3 discrete states with strict ordering

## Prohibited Actions

- Instructing subagents to perform actual work
- Making code changes
- Creating commits
- Manually editing cache to fake transitions
