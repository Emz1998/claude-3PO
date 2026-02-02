---
name: dry-run
description: Dry run the /implement workflow to test guardrail enforcement
argument-hint: <milestone-id> [tdd|ta|default]
model: opus
---

## Instructions

- This is a **test run** for the /implement workflow guardrail
- Verify guardrail blocks out-of-order subagent calls
- Proceed until the end unless a guardrail fully blocks you
- If you need help, stop and ask user for help

## Workflow Test Sequence

Trigger the following sequence of transitions with Skill tool.

`explore` → `plan` → `plan-consult` → `finalize-plan` → `write-test` → `review-test` → `write-code` → `code-review` → `refactor` → `validate` → `commit`

## Phase Reminders Verification

At each phase transition, verify phase reminder injection:

**Test 1: Reminder Loaded**
- Check that phase reminder appears in context
- Verify reminder matches expected phase name

**Test 2: Content Structure**
- Verify reminder contains: Purpose, Deliverables, Key Focus, Next Phase
- Exception: `commit` phase has "Workflow Complete" instead of Next Phase

**Test 3: File Source**
- Confirm reminders load from `config/reminders/{phase}.md`
- Report if fallback default is used instead

**Report Format (per phase):**
```
[PHASE] {phase-name}
- Reminder: LOADED | FALLBACK | MISSING
- Structure: VALID | INVALID
- Content length: {chars}
```

## Deliverables Verification

At each phase, verify deliverables tracking:

**Test 1: Priority Order**
- Verify Priority 1 (read) completes before Priority 2 (write)
- Guardrail should block write if read not completed

**Test 2: File Pattern Matching**
- Verify files match expected patterns from workflow_config.json
- Check read/write actions recorded correctly

**Test 3: Deliverable Chain**
| Phase | Read | Write |
|-------|------|-------|
| explore | `prompt.md` | `codebase-status/*.md` |
| plan | `codebase-status/*.md` | `plans/initial-plan_*.md` |
| plan-consult | `plans/initial-plan_*.md` | `plans/plan-consultation_*.md` |
| finalize-plan | `plans/plan-consultation_*.md` | `plans/final-plan_*.md` |
| write-test | `plans/final-plan_*.md` | `tests/test-summary_*.md` |
| review-test | `tests/test-summary_*.md` | `tests/test-quality-report_*.md` |
| write-code | `plans/final-plan_*.md` | `misc/code-test_*.md` |
| code-review | `misc/code-test_*.md` | `reviews/code-review_*.md` |
| refactor | `reviews/code-review_*.md` | `reports/refactor_*.md` |
| validate | `reports/refactor_*.md` | `reports/validation_report_*.md` |
| commit | `reports/validation_report_*.md` | `reports/commit_*.md` |

**Report Format (per phase):**
```
[DELIVERABLE] {phase-name}
- Read: PASS | FAIL | SKIPPED
- Write: PASS | FAIL | SKIPPED
- Order: VALID | INVALID
```

## Prohibited Actions

- Do not make code changes
- Do not create commits
- Do not manually edit cache to fake transitions
- Do not modify reminder files
- Do not modify phase_reminders.py

## Context Memory

- Track test results per phase
- Report summary at workflow end
