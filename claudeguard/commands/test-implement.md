---
name: test-implement
description: Live E2E test of implement workflow guardrails
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent, WebFetch
model: haiku
---

You are a **guardrail test runner** for the **implement workflow**. Your job is to systematically test every guardrail by deliberately doing wrong things first (which MUST be blocked), then doing the correct thing to advance.

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' implement ${CLAUDE_SESSION_ID} --tdd SK-TEST`

## How This Works

1. At each phase, you will attempt **forbidden actions** that should be blocked by the guardrails.
2. After each block, record it as a **PASS** (block was expected).
3. If a forbidden action is NOT blocked, record it as a **FAIL**.
4. Then perform the **correct action** to advance to the next phase.
5. At the end, present a test report.

**Important**: When you get blocked, that is the EXPECTED outcome. Do NOT treat blocks as errors. Record them as passing tests.

**Important**: All subagents must exit immediately. Do NOT let them do real work — we are testing guardrails, not functionality. Every agent prompt must instruct the agent to respond with ONLY the required output format (scores, verdicts, etc.) and nothing else. Keep prompts under 2 sentences. Example: "Do not read any files. Respond with exactly: Confidence Score: 95\nQuality Score: 95"

## Test Report Format

Track results in this format and present at the end:

```
| Phase | Test | Expected | Actual | Result |
|-------|------|----------|--------|--------|
| explore | Write file | BLOCK | BLOCK | PASS |
```

---

## Test Sequence

Execute each step in order. For each "TRY" step, attempt the action. For each "DO" step, perform the correct action.

### explore + research (parallel)

**Start**: Invoke `/explore` and `/research` in parallel (both as skills in the same message).

**TRY (expect BLOCK):**
- Write a file: `Write` to `test-guardrail.py` — should block (read-only phase)
- Invoke wrong agent: `Agent` with `subagent_type: "Plan"` — should block (expected: Explore)

**TRY (expect ALLOW):**
- Read-only command: `Bash` with `ls -la` — should allow
- Explore agent: `Agent` with `subagent_type: "Explore"`, description: "Test", prompt: "Respond with exactly: Done." — should allow

**DO**: Invoke 2 more Explore agents and 2 Research agents (total 3 Explore + 2 Research) with the same minimal prompt. Wait for all to complete.

### plan (implement template)

**DO**: Invoke `/plan`.

**DO**: Invoke `Agent` with `subagent_type: "Plan"`, description: "Test", prompt: "Respond with exactly: Done." — wait for completion.

**TRY (expect BLOCK) — implement plan validation:**
- Write build-style plan (wrong template): `Write` to `.claude/plans/latest-plan.md` with content `# Plan\n\n## Dependencies\n- flask\n\n## Contracts\n- UserService\n\n## Tasks\n- Build login\n` — should block (implement requires Context, Approach, Files to Create/Modify, Verification)
- Write plan missing Context: `Write` to `.claude/plans/latest-plan.md` with content `# Plan\n\n## Approach\nDo stuff.\n\n## Files to Create/Modify\n\n| Action | Path |\n|--------|------|\n| Create | src/app.py |\n\n## Verification\nTest it.\n` — should block
- Write plan missing Files to Create/Modify: `Write` to `.claude/plans/latest-plan.md` with content `# Plan\n\n## Context\nSome context.\n\n## Approach\nDo stuff.\n\n## Verification\nTest it.\n` — should block

**TRY (expect ALLOW):**
- Write valid implement plan: `Write` to `.claude/plans/latest-plan.md` with this content:

```
# Test Plan

## Context
Testing implement guardrails.

## Approach
Create a hello function in src/hello.py.

## Files to Create/Modify

| Action | Path |
|--------|------|
| Create | src/hello.py |
| Create | src/utils.py |

## Verification

Run pytest.
```

### plan-review

**DO**: Invoke `/plan-review`.

**TRY (expect BLOCK):**
- Edit wrong file: `Edit` on `wrong.md` — should block

**TRY (expect ALLOW):**
- Edit plan file: `Edit` on `.claude/plans/latest-plan.md`, old_string: "Testing implement guardrails", new_string: "Testing implement workflow guardrails" — should allow

**DO**: Invoke `Agent` with `subagent_type: "PlanReview"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\nConfidence Score: 95\nQuality Score: 95"

Wait for completion. The workflow should **discontinue** (checkpoint). This is expected.

### create-tasks (AUTO)

After plan-review passes, create-tasks should auto-start.

**TRY (expect BLOCK):**
- Invoke `/create-tasks` as skill — should block (auto-phase)

**Note**: The create-tasks phase waits for project tasks to have subtasks. For testing, we cannot easily simulate this via tool calls. Record the auto-phase skill block test and move on.

### write-tests (AUTO, TDD)

**TRY (expect BLOCK):**
- Invoke `/write-tests` as skill — should block (auto-phase)
- Write non-test file: `Write` to `app.py` — should block (test files only)

**TRY (expect ALLOW):**
- Write test file: `Write` to `test_hello.py` with content:
```python
def test_hello():
    from hello import hello
    assert hello() is None
```
- Run tests: `Bash` with `python -m pytest test_hello.py -v` — should allow

### tests-review

**DO**: Invoke `/tests-review`.

**TRY (expect BLOCK):**
- Edit unknown file: `Edit` on `unknown.py` — should block (not a test file in session)

**TRY (expect ALLOW):**
- Edit test file: `Edit` on `test_hello.py`, old_string: `assert hello() is None`, new_string: `assert hello() is None  # verified` — should allow

**DO**: Invoke `Agent` with `subagent_type: "TestReviewer"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\n## Files to revise\n- test_hello.py\n\nPass"

### write-code (AUTO — implement file guard)

After tests-review passes, write-code should auto-start.

**TRY (expect BLOCK) — implement file guard:**
- Invoke `/write-code` as skill — should block (auto-phase)
- Write unlisted file: `Write` to `src/other.py` with content `x = 1` — should block (not in Files to Create/Modify)
- Write markdown: `Write` to `readme.md` — should block (not in Files to Create/Modify)

**TRY (expect ALLOW) — implement file guard:**
- Write listed file: `Write` to `src/hello.py` with content `def hello(): return "hello"` — should allow (in Files to Create/Modify)
- Write another listed file: `Write` to `src/utils.py` with content `# utils` — should allow (in Files to Create/Modify)
- Run tests: `Bash` with `python -m pytest test_hello.py -v` — should allow

### validate (implement's quality-check)

**DO**: Invoke `/validate`.

**DO**: Invoke `Agent` with `subagent_type: "QASpecialist"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\nPass"

### code-review

**DO**: Invoke `/code-review`.

**TRY (expect BLOCK):**
- Edit file not in session: `Edit` on `random.py` — should block

**TRY (expect ALLOW):**
- Edit code file in session: `Edit` on `src/hello.py`, old_string: `return "hello"`, new_string: `return "hello world"` — should allow

**DO**: Invoke `Agent` with `subagent_type: "CodeReviewer"`, description: "Test", prompt: "Do not read any files. Respond with exactly:\n\nConfidence Score: 95\nQuality Score: 92\n\n## Files to revise\n- src/hello.py\n\n## Tests to revise\n- test_hello.py"

### pr-create

**DO**: Invoke `/pr-create`.

**TRY (expect BLOCK):**
- PR create without --json: `Bash` with `gh pr create --title test` — should block

**TRY (expect ALLOW):**
- Git read command: `Bash` with `git status` — should allow

**Note**: Skip actual PR creation. Move to next phase.

### ci-check

**DO**: Invoke `/ci-check`.

**TRY (expect BLOCK):**
- CI check without --json: `Bash` with `gh pr checks` — should block

**Note**: Skip actual CI check. Move to next phase.

### write-report

**DO**: Invoke `/write-report`.

**TRY (expect BLOCK):**
- Write code file: `Write` to `feature.py` — should block (report phase, only report path)

**TRY (expect ALLOW):**
- Write report: `Write` to `.claude/reports/report.md` with content `# Test Report\n\nAll implement guardrails tested.` — should allow

---

## Final Report

Present the test results table. Count total tests, PASS, and FAIL.

Clean up any test files created (`test_hello.py`, `src/hello.py`, `src/utils.py`).

If all tests pass: **All implement guardrails verified.**
If any fail: **GUARDRAIL FAILURES DETECTED — investigate before using in production.**
