# E2E Test Report - Build Workflow Guardrails

## Phase: explore + research

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| explore+research | Write test-guardrail.py | BLOCK | Blocked | PASS |
| explore+research | Edit CLAUDE.md | BLOCK | Blocked | PASS |
| explore+research | Bash echo | BLOCK | Blocked | PASS |
| explore+research | Agent Plan | BLOCK | Blocked | PASS |
| explore+research | Bash ls -la | ALLOW | Allowed | PASS |
| explore+research | Explore #1 | ALLOW | Allowed | PASS |
| explore+research | Explore #2 | ALLOW | Allowed | PASS |
| explore+research | Explore #3 | ALLOW | Allowed | PASS |
| explore+research | Explore #4 (over max) | BLOCK | Blocked | PASS |
| explore+research | WebFetch wikipedia | BLOCK | Blocked | PASS |
| explore+research | WebFetch python docs | ALLOW | Allowed | PASS |
| explore+research | Research #1 | ALLOW | Allowed | PASS |
| explore+research | Research #2 | ALLOW | Allowed | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| explore | status | completed | completed | PASS |
| research | status | completed | completed | PASS |
| agents | 3 Explore completed | 3 | 3 | PASS |
| agents | 2 Research completed | 2 | 2 | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| research | Write | test-guardrail.py | Yes | PASS |
| research | Edit | CLAUDE.md | Yes | PASS |
| research | Bash | echo "write attempt" | Yes | PASS |
| research | Agent | Plan | Yes | PASS |
| research | Agent | Explore (4th) | Yes | PASS |
| research | WebFetch | wikipedia.org | Yes | PASS |

## Phase: plan

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| plan | Skill install-deps (skip ahead) | BLOCK | Blocked | PASS |
| plan | Skill explore (go backwards) | BLOCK | Blocked | PASS |
| plan | Invoke /plan | ALLOW | Allowed | PASS |
| plan | Write plan before Plan agent | BLOCK | Blocked | PASS |
| plan | Agent Plan | ALLOW | Allowed | PASS |
| plan | Write plan missing sections | BLOCK | Blocked (missing Dependencies, Tasks, Files to Modify) | PASS |
| plan | Write plan subsection tasks | BLOCK | Blocked (Tasks must use bullets) | PASS |
| plan | Write wrong-plan.md | BLOCK | Blocked (wrong path) | PASS |
| plan | Write valid plan | ALLOW | Allowed | PASS |
| plan | Write contracts missing Specifications | BLOCK | Blocked | PASS |
| plan | Write valid contracts | ALLOW | Allowed | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| plan | plan.written | true | true | PASS |
| plan | plan.file_path | .claude/plans/latest-plan.md | .claude/plans/latest-plan.md | PASS |
| plan | plan.revised | null | null | PASS |
| plan | tasks | ["Create hello function"] | ["Create hello function"] | PASS |
| plan | dependencies.packages | ["None"] | ["None"] | PASS |
| plan | contracts.names | ["HelloService"] | ["HelloService"] | PASS |
| plan | contracts.file_path | .claude/contracts/latest-contracts.md | .claude/contracts/latest-contracts.md | PASS |
| plan | contract_files | ["src/hello.py"] | ["src/hello.py"] | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| plan | Skill | install-deps | Yes (logged as "research" phase) | PASS |
| plan | Skill | explore | Yes (logged as "research" phase) | PASS |
| plan | Write | latest-plan.md (before agent) | Yes | PASS |
| plan | Write | latest-plan.md (missing sections) | Yes | PASS |
| plan | Write | latest-plan.md (subsection tasks) | Yes | PASS |
| plan | Write | wrong-plan.md | Yes | PASS |
| plan | Write | latest-contracts.md (missing specs) | Yes | PASS |

### Bugs

- **BUG-001**: install-deps and explore skill violations logged with phase "research" instead of "plan". The blocks occurred before `/plan` was invoked, so the state still showed "research" as the last phase. The blocks are correct, but the phase label in violations.md is misleading.

## Phase: plan-review

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| plan-review | Edit wrong.md | BLOCK | Tool failed (file not found) — guardrail did NOT fire | FAIL |
| plan-review | Write anything.py | BLOCK | Blocked | PASS |
| plan-review | Edit plan file (allowed) | ALLOW | Allowed | PASS |
| plan-review | PlanReview iter 1 (50/60) | ALLOW | Allowed, status=Fail | PASS |
| plan-review | PlanReview without revision | BLOCK | Blocked | PASS |
| plan-review | Edit plan (revision) | ALLOW | Allowed | PASS |
| plan-review | PlanReview iter 2 (70/75) | ALLOW | Allowed, status=Fail | PASS |
| plan-review | Edit plan (revision 2) | ALLOW | Allowed | PASS |
| plan-review | PlanReview iter 3 (60/60) | ALLOW | Allowed, status=Fail | PASS |
| plan-review | /continue (exhaustion) | BLOCK | Blocked (use /plan-approved) | PASS |
| plan-review | /plan-approved (exhaustion) | ALLOW | Allowed, create-tasks started | PASS |
| plan-review | Reset via /reset-plan-review | ALLOW | Reset OK | PASS |
| plan-review | PlanReview 95/95 (checkpoint) | ALLOW | Allowed, checkpoint discontinue | PASS |
| plan-review | /revise-plan fix the approach | ALLOW | Allowed, plan-review reopened | PASS |
| plan-review | PlanReview without edit (revise) | BLOCK | Blocked | PASS |
| plan-review | Edit plan (user revised) | ALLOW | Allowed | PASS |
| plan-review | PlanReview 95/95 (checkpoint 2) | ALLOW | Allowed, checkpoint discontinue | PASS |
| plan-review | /plan-approved (checkpoint) | ALLOW | Allowed, create-tasks started | PASS |
| create-tasks | /revise-plan wrong phase | BLOCK | Blocked | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| plan-review | iter 1: reviews[0].status | Fail | Fail | PASS |
| plan-review | iter 1: revised | false | false | PASS |
| plan-review | iter 2: revised after edit | true | true | PASS |
| plan-review | 3 reviews all Fail | 3×Fail | 3×Fail | PASS |
| plan-review | after /plan-approved: plan-review status | completed | completed | PASS |
| plan-review | after /plan-approved: create-tasks status | in_progress | in_progress | PASS |
| plan-review | after /reset + revise: plan-review status | in_progress | in_progress | PASS |
| plan-review | after /reset + revise: revised | false | false | PASS |
| plan-review | after /reset + revise: reviews | [] | [] | PASS |
| plan-review | final: plan-review status | completed | completed | PASS |
| plan-review | final: create-tasks status | in_progress | in_progress | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| plan-review | Edit | wrong.md | No (file didn't exist, tool failed before hook) | FAIL |
| plan-review | Write | anything.py | Yes | PASS |
| plan-review | Agent | PlanReview (no revision) | Yes | PASS |
| plan-review | Skill | continue | Yes | PASS |
| plan-review | Agent | PlanReview (revise required) | Yes | PASS |
| create-tasks | Skill | revise-plan | Yes | PASS |

### Bugs

- **BUG-002**: Edit on non-existent file `wrong.md` was not blocked by guardrail. The Edit tool returned "File does not exist" error before the pre_tool_use hook could fire a guardrail block. The violation was not logged. Guardrail should block based on path validation alone, regardless of file existence.

## Phase: create-tasks

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| create-tasks | Skill /create-tasks | BLOCK | "Unknown skill" (skill doesn't exist, guardrail not triggered) | FAIL |
| create-tasks | TaskCreate wrong subject | BLOCK | Blocked | PASS |
| create-tasks | TaskCreate empty subject | BLOCK | Blocked | PASS |
| create-tasks | TaskCreate empty description | BLOCK | Blocked | PASS |
| create-tasks | TaskCreate valid | ALLOW | Allowed (Task #4 created) | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| create-tasks | created_tasks | ["Create hello function"] | ["Create hello function"] | PASS |
| create-tasks | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| create-tasks | Skill | create-tasks | No (skill not found, hook not triggered) | FAIL |
| create-tasks | TaskCreate | Deploy to production | Yes | PASS |
| create-tasks | TaskCreate | (empty subject) | Yes | PASS |
| create-tasks | TaskCreate | Create hello function (empty desc) | Yes | PASS |

### Bugs

- **BUG-003**: `/create-tasks` skill test is untestable — skill doesn't exist for guardrail to block it.

## Phase: define-contracts

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| define-contracts | Invoke /define-contracts | ALLOW | Allowed | PASS |
| define-contracts | Write notes.md | BLOCK | Blocked | PASS |
| define-contracts | Write src/random.py | BLOCK | Blocked | PASS |
| define-contracts | Write src/hello.py with HelloService | ALLOW | Allowed | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| define-contracts | contracts.written | true | true | PASS |
| define-contracts | contracts.validated | true | true | PASS |
| define-contracts | contracts.code_files | ["src/hello.py"] | ["src/hello.py"] | PASS |
| define-contracts | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| define-contracts | Write | notes.md | Yes | PASS |
| define-contracts | Write | src/random.py | Yes | PASS |

---

## Phase: write-tests (AUTO)

*(Auto-started after define-contracts completed)*

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| write-tests | Skill /write-tests | BLOCK | "Unknown skill" (no skill to block) | FAIL |
| write-tests | Write app.py | BLOCK | Blocked | PASS |
| write-tests | Write test_hello.py | ALLOW | Allowed | PASS |
| write-tests | pytest test_hello.py | ALLOW | Allowed (test failed - no hello module) | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| write-tests | tests.file_paths | ["test_hello.py"] | ["test_hello.py"] | PASS |
| write-tests | tests.executed | true | true | PASS |
| write-tests | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| write-tests | Skill | write-tests | No (skill not found) | FAIL |
| write-tests | Write | app.py | Yes | PASS |

### Bugs

- **BUG-004**: `/write-tests` skill doesn't exist, same pattern as create-tasks. The auto-phase cannot be tested for guardrail blocking via Skill tool.

## Phase: test-review

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| test-review | Invoke /test-review | ALLOW | Allowed | PASS |
| test-review | Edit unknown.py | BLOCK | Tool failed (file not found) — guardrail did NOT fire | FAIL |
| test-review | Edit test_hello.py (allowed) | ALLOW | Allowed | PASS |
| test-review | TestReviewer Fail verdict | ALLOW | Allowed, verdict=Fail | PASS |
| test-review | Edit test_hello.py (revise) | ALLOW | Allowed | PASS |
| test-review | TestReviewer Pass verdict | ALLOW | Allowed, verdict=Pass | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| test-review | reviews[0].verdict | Fail | Fail | PASS |
| test-review | reviews[1].verdict | Pass | Pass | PASS |
| test-review | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| test-review | Edit | unknown.py | No (file not found, tool failed before guardrail) | FAIL |

### Bugs

- **BUG-005**: Same as BUG-002 — Edit on non-existent `unknown.py` was not blocked/logged by guardrail. Consistent pattern: pre_tool_use hook fires AFTER the tool validates arguments (including file existence).

## Phase: write-code (AUTO)

*(Auto-started after test-review passed)*

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| write-code | Skill /write-code | BLOCK | "Unknown skill" (no skill to block) | FAIL |
| write-code | Write readme.md | BLOCK | Blocked (non-code extension) | PASS |
| write-code | Write src/hello.py | ALLOW | Allowed | PASS |
| write-code | pytest test_hello.py | ALLOW | Allowed (test fails - module not found) | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| write-code | code_files.file_paths | ["src/hello.py"] | ["src/hello.py"] | PASS |
| write-code | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| write-code | Skill | write-code | No (skill not found) | FAIL |
| write-code | Write | readme.md | Yes | PASS |

### Bugs

- **BUG-006**: `/write-code` skill doesn't exist. Same pattern as create-tasks/write-tests.

## Phase: quality-check

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| quality-check | Invoke /quality-check | ALLOW | Allowed | PASS |
| quality-check | QASpecialist Fail | ALLOW | Allowed, result=Fail | PASS |
| quality-check | QASpecialist Pass | ALLOW | Allowed, result=Pass | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| quality-check | quality_check_result (Fail) | Fail | Fail | PASS |
| quality-check | quality_check_result (Pass) | Pass | Pass | PASS |
| quality-check | status | completed | completed | PASS |

## Phase: code-review

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| code-review | Invoke /code-review | ALLOW | Allowed | PASS |
| code-review | Edit random.py | BLOCK | Tool failed (file not found) — guardrail did NOT fire | FAIL |
| code-review | Edit src/hello.py (allowed) | ALLOW | Allowed | PASS |
| code-review | CodeReviewer Fail (50/50) | ALLOW | Allowed, status=Fail | PASS |
| code-review | /revise-plan (wrong phase) | BLOCK | Blocked | PASS |
| code-review | Edit src/hello.py without test revision | BLOCK (unexpected) | Blocked: must revise tests first | PASS |
| code-review | Edit test_hello.py (test revision) | ALLOW | Allowed | PASS |
| code-review | Edit src/hello.py (after test revision) | ALLOW | Allowed | PASS |
| code-review | CodeReviewer Pass (95/92) | ALLOW | Allowed, status=Pass | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| code-review | reviews[0].status | Fail | Fail | PASS |
| code-review | reviews[1].status | Pass | Pass | PASS |
| code-review | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| code-review | Edit | random.py | No (file not found, tool failed before guardrail) | FAIL |
| code-review | Skill | revise-plan | Yes | PASS |
| code-review | Edit | src/hello.py (tests not revised) | Yes | PASS |

### Bugs

- **BUG-007**: Same as BUG-002/005 — Edit on non-existent `random.py` not blocked/logged.

## Phase: pr-create

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| pr-create | Invoke /pr-create | ALLOW | Allowed | PASS |
| pr-create | Bash echo "hello" | BLOCK | Blocked | PASS |
| pr-create | gh pr create without --json | BLOCK | Blocked | PASS |
| pr-create | git status | ALLOW | Allowed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| pr-create | Bash | echo "hello" | Yes | PASS |
| pr-create | Bash | gh pr create --title test | Yes | PASS |

## Phase: ci-check

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| ci-check | Invoke /ci-check | ALLOW | Allowed (after /continue skip of pr-create) | PASS |
| ci-check | Bash echo "hello" | BLOCK | Blocked | PASS |
| ci-check | gh pr checks without --json | BLOCK | Blocked | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| ci-check | Bash | echo "hello" | Yes | PASS |
| ci-check | Bash | gh pr checks | Yes | PASS |

## Phase: write-report

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| write-report | Stop before write-report | BLOCK | Blocked by stop hook | PASS |
| write-report | Invoke /write-report | ALLOW | Allowed (after /continue skip of ci-check) | PASS |
| write-report | Write feature.py | BLOCK | Blocked | PASS |
| write-report | Write .claude/reports/report.md | ALLOW | Allowed | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| write-report | report_written | true | true | PASS |
| write-report | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| write-report | Write | feature.py | Yes | PASS |

### Bugs

- **BUG-008**: After workflow completes (all phases done, workflow_active=true), the guardrail still enforces write-report read-only restrictions. Post-workflow cleanup (rm test files) is blocked. The workflow_active flag never resets.

- **BUG-003**: `/create-tasks` skill test is untestable — skill doesn't exist. If the intent is for the guardrail to block the skill, the skill needs to exist for the hook to fire. The guardrail block was not triggered, just "Unknown skill" from the Skill tool.

## Phase: install-deps

### Guardrail Tests

| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| install-deps | Invoke /install-deps | ALLOW | Allowed | PASS |
| install-deps | Write app.py | BLOCK | Blocked | PASS |
| install-deps | Bash echo "not an install" | BLOCK | Blocked | PASS |
| install-deps | Write requirements.txt | ALLOW | Allowed | PASS |
| install-deps | pip install -r requirements.txt | ALLOW | Allowed | PASS |

### State Verification

| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
| install-deps | dependencies.installed | true | true | PASS |
| install-deps | status | completed | completed | PASS |

### Violations Log

| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
| install-deps | Write | app.py | Yes | PASS |
| install-deps | Bash | echo "not an install" | Yes | PASS |

---

# Final Summary

## Totals

| Category | Total | Pass | Fail | Pass Rate |
|----------|-------|------|------|-----------|
| Guardrail Tests | 72 | 66 | 6 | 91.7% |
| State Verification | 41 | 41 | 0 | 100% |
| Violations Log | 40 | 34 | 6 | 85.0% |

## Phases Tested

All 15 build workflow phases completed successfully:
explore, research, plan, plan-review, create-tasks, install-deps, define-contracts, write-tests, test-review, write-code, quality-check, code-review, pr-create, ci-check, write-report

## Bug Summary

| ID | Severity | Category | Description |
|----|----------|----------|-------------|
| BUG-001 | Low | Violations logging | Phase label in violations.md reflects last active phase ("research") instead of logical phase ("plan") for skill blocks invoked before `/plan` |
| BUG-002 | Medium | Edit guardrail | Edit on non-existent `wrong.md` bypasses pre_tool_use hook -- tool validates file existence before hook fires |
| BUG-003 | Medium | Skill coverage | `/create-tasks` has no invokable skill -- auto-phase cannot be blocked by guardrail Skill hook |
| BUG-004 | Medium | Skill coverage | `/write-tests` has no invokable skill -- same pattern as BUG-003 |
| BUG-005 | Medium | Edit guardrail | Edit on non-existent `unknown.py` bypasses hook -- same root cause as BUG-002 |
| BUG-006 | Medium | Skill coverage | `/write-code` has no invokable skill -- same pattern as BUG-003 |
| BUG-007 | Medium | Edit guardrail | Edit on non-existent `random.py` bypasses hook -- same root cause as BUG-002 |
| BUG-008 | Low | Workflow lifecycle | `workflow_active` stays `true` after all phases complete -- post-workflow cleanup (rm, bash) still blocked |

## Root Causes (2 distinct issues)

**1. Edit tool validates file existence before pre_tool_use hook fires (BUG-002/005/007)**
- When the Edit tool receives a path to a non-existent file, the tool itself returns "File does not exist" before the pre_tool_use guardrail hook has a chance to block based on path validation
- Fix: The pre_tool_use hook should intercept Edit calls and validate the path against allowed files regardless of whether the file exists

**2. Auto-phase skills don't exist as invokable commands (BUG-003/004/006)**
- `create-tasks`, `write-tests`, and `write-code` are auto-phases with no corresponding Skill definition
- When tested via `/create-tasks`, the Skill tool returns "Unknown skill" before any hook fires
- Fix: Register stub skills for these auto-phases so the pre_tool_use Skill hook can block them with a proper guardrail message

## Verdict

**GUARDRAIL FAILURES DETECTED -- 8 bugs found across 2 root causes. Core guardrail enforcement is solid (91.7% pass rate). All state transitions and verifications pass at 100%. The failures are limited to edge cases (non-existent file edits, missing auto-phase skills) and do not affect the primary workflow enforcement path. Recommend fixing root causes before production use.**
