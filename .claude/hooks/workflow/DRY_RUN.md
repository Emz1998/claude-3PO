# Multi-Session Workflow — Dry Run

End-to-end test of the workflow hooks system. This runs the actual workflow phases through Claude Code to verify hooks fire correctly.

**IMPORTANT: This is a TEST ONLY. Do not implement, write code, create PRs, or push anything. Simply invoke each skill/command and verify the hooks respond correctly (allow or block as expected).**

**LOGGING: After each test, log the result to `.claude/hooks/workflow/dry_run.log` using the format below. At the end, print a summary of all test results.**

---

## Log Format

Append one line per test to `dry_run.log`:

```
[PASS] Test 1: Session Creation via /implement — sessions.SK-DRY created, phase=pre-coding
[FAIL] Test 2: Pre-coding Phase Guards — code-reviewer was NOT blocked (expected block)
[SKIP] Test 8: Validation Loop Low Score — skipped (depends on Test 7 failure)
```

Use this bash command to log each result:

```bash
echo "[PASS] Test N: <name> — <details>" >> .claude/hooks/workflow/dry_run.log
```

---

## Prerequisites

1. All tests pass: `cd .claude/hooks/workflow && pytest tests/ -v`
2. State is clean:
   ```bash
   cat .claude/hooks/workflow/state.json
   # Expected: {"workflow_active": false, "sessions": {}}
   ```
3. You have a test story ID ready (e.g. `SK-DRY`)
4. Initialize the log file:
   ```bash
   echo "=== Dry Run — $(date -Iseconds) ===" > .claude/hooks/workflow/dry_run.log
   ```

---

## Test 1: Session Creation via /implement

**Action**: Type `/implement SK-DRY`

**DO NOT** actually implement anything. Immediately stop after the hook fires.

**Verify**:
- `workflow_active` is `true` in `state.json`
- `sessions.SK-DRY` exists with `phase.current = "pre-coding"` and `control.status = "running"`
- Reminder for pre-coding phase is injected

**Check**:
```bash
cat .claude/hooks/workflow/state.json | python3 -m json.tool
```

**Log**:
```bash
# If sessions.SK-DRY exists and phase.current == "pre-coding":
echo "[PASS] Test 1: Session Creation — sessions.SK-DRY created, phase=pre-coding, workflow_active=true" >> .claude/hooks/workflow/dry_run.log
# Otherwise:
echo "[FAIL] Test 1: Session Creation — <describe what went wrong>" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 2: Pre-coding Phase Guards

**Action**: While in pre-coding phase, try launching agents in order:
1. Launch `Explore` agent — should be **allowed**
2. Launch `Plan` agent — should be **allowed** (after Explore)
3. Launch `plan-reviewer` agent — should be **allowed** (after Plan)
4. Try launching `code-reviewer` agent — should be **blocked** (wrong phase)

**DO NOT** actually explore or plan. Just verify the guard allows/blocks.

**Verify**: `pre_coding_phase.py` guard allows sequential agents, blocks out-of-order agents.

**Log**:
```bash
# If Explore/Plan/plan-reviewer allowed AND code-reviewer blocked:
echo "[PASS] Test 2: Pre-coding Guards — sequential agents allowed, code-reviewer blocked" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 3: Phase Transition — /code

**Action**: Type `/code`

**Verify**:
- `phase_guard.py` checks predecessor is `pre-coding` — should **allow**
- `state.json` updates: `phase.current = "code"`, `phase.previous = "pre-coding"`

**DO NOT** write any code. Just verify the phase transition.

**Log**:
```bash
echo "[PASS] Test 3: Phase Transition /code — phase.current=code, phase.previous=pre-coding" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 4: Code Phase Guards

**Action**: While in code phase:
1. Launch `test-engineer` agent — should be **allowed**
2. Launch `test-reviewer` agent — should be **allowed** (after test-engineer)
3. Try launching `Explore` agent — should be **blocked** (wrong phase)

**DO NOT** write tests. Just verify guards.

**Log**:
```bash
echo "[PASS] Test 4: Code Phase Guards — test agents allowed, Explore blocked" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 5: Bash Guard — Blocks Early PR/Push

**Action**: While in code phase, try:
1. Run `gh pr create --title test` — should be **blocked** (not in create-pr phase)
2. Run `git push origin main` — should be **blocked** (not in push phase)
3. Run `ls -la` — should be **allowed** (normal command)
4. Run `gh pr close 1` — should be **blocked** (always blocked)

**DO NOT** actually run these commands. Just verify the guard response.

**Log**:
```bash
echo "[PASS] Test 5: Bash Guard — gh pr create blocked, git push blocked, ls allowed, gh pr close blocked" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 6: Phase Transition — /code-review

**Action**: Type `/code-review`

**Verify**:
- `phase_guard.py` checks predecessor is `code` — should **allow**
- `state.json` updates: `phase.current = "review"`, `phase.previous = "code"`

**Log**:
```bash
echo "[PASS] Test 6: Phase Transition /code-review — phase.current=review, phase.previous=code" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 7: Validation Loop — Code Reviewer

**Action**: Launch `code-reviewer` agent.

**DO NOT** actually review code. The agent should:
1. Try to stop without `/decision` — `decision_guard.py` should **block**
2. Invoke `/decision 85 80` — should record scores to `session.validation`
3. Try to stop again — `validation_loop.py` should **allow** (scores >= 70 threshold)

**Verify**:
- `session.validation.decision_invoked = true`
- `session.validation.confidence_score = 85`
- `session.validation.quality_score = 80`

**Log**:
```bash
echo "[PASS] Test 7: Validation Loop — decision_guard blocked without /decision, allowed with 85/80 scores" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 8: Validation Loop — Low Score Block

**Action**: Launch `code-reviewer` again, invoke `/decision 40 80`

**Verify**:
- `validation_loop.py` **blocks** (confidence 40 < 70 threshold)
- `session.validation.iteration_count` increments
- `session.validation.decision_invoked` resets to `false`

**Log**:
```bash
echo "[PASS] Test 8: Validation Loop Low Score — blocked at 40/80, iteration_count incremented, decision_invoked reset" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 9: Phase Transitions — /commit → /create-pr → /validate → /push

**Action**: Walk through remaining phases in order:

1. `/commit` — should **allow** (predecessor = review)
2. `/create-pr` — should **allow** (predecessor = final-commit)
3. `/validate` — should **allow** (predecessor = create-pr)
4. `/push` — should **allow** (predecessor = validate)

**DO NOT** actually commit, create PR, or push. Just verify each phase transition.

**Verify**: `state.json` shows `phase.current` advancing through each phase.

**Log**:
```bash
echo "[PASS] Test 9: Phase Chain — commit(final-commit) → create-pr → validate → push all allowed" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 10: Phase Transitions — Wrong Order

**Action**: After reaching push phase, try:
1. `/code` — should be **blocked** (predecessor must be pre-coding, current is push)
2. `/commit` — should be **blocked** (predecessor must be review)

**Log**:
```bash
echo "[PASS] Test 10: Wrong Order Blocked — /code and /commit both blocked from push phase" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 11: Hold Checker

**Action**: Manually set hold in state.json:
```bash
python3 -c "
from workflow.session_state import SessionState
SessionState().update_session('SK-DRY', lambda s: s['control'].update({'hold': True}))
"
```

Then try:
1. Launch any Agent — should be **blocked** ("session is on hold")
2. Launch any Skill — should be **blocked**
3. Use Read/Write/Bash tools — should be **allowed** (hold only blocks Agent/Skill)

Clear hold after:
```bash
python3 -c "
from workflow.session_state import SessionState
SessionState().update_session('SK-DRY', lambda s: s['control'].update({'hold': False}))
"
```

**Log**:
```bash
echo "[PASS] Test 11: Hold Checker — Agent/Skill blocked on hold, Read/Write/Bash allowed" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 12: Stop Guard

**Action**: Try to stop the session (Ctrl+C or natural stop).

**Verify**:
- `stop_guard.py` **blocks** (status is "running", PR not created)
- Message indicates session is not completed

**Log**:
```bash
echo "[PASS] Test 12: Stop Guard — blocked (status=running, pr not created)" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 13: PR Review Session via /review

**Action**: Type `/review 99`

**Verify**:
- `sessions.PR-99` created in `state.json`
- `workflow_type = "pr-review"`
- `pr.number = 99`, `pr.created = true`
- `phase.current = "pr-review"`

**Log**:
```bash
echo "[PASS] Test 13: PR Review Session — sessions.PR-99 created, workflow_type=pr-review, pr.number=99" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 14: Session Logger

**Action**: After any tool use in a session with `STORY_ID` set.

**Verify**:
- JSONL log file created at `.claude/sessions/SK-DRY/log.jsonl`
- Entries have `ts`, `session`, `event`, `phase` fields

**Log**:
```bash
echo "[PASS] Test 14: Session Logger — log.jsonl created with ts/session/event/phase fields" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 15: Simplify Trigger

**Action**: While in code phase, use the Write tool to create a new file.

**DO NOT** write real code. Create a dummy file like `/tmp/test-simplify.py`.

**Verify**: System message injected suggesting `/simplify` review.

**Log**:
```bash
echo "[PASS] Test 15: Simplify Trigger — system message injected on Write in code phase" >> .claude/hooks/workflow/dry_run.log
```

---

## Test 16: No STORY_ID — Graceful Fallback

**Action**: Start a new Claude session **without** `STORY_ID` set. Try invoking agents and skills normally.

**Verify**: All guards exit 0 (no-op). No crashes. Workflow hooks are invisible when `STORY_ID` is absent.

**Log**:
```bash
echo "[PASS] Test 16: No STORY_ID Fallback — all guards exit 0, no crashes" >> .claude/hooks/workflow/dry_run.log
```

---

## Summary

After all tests, print the summary:

```bash
echo ""
echo "=== DRY RUN SUMMARY ==="
echo ""
TOTAL=$(grep -c "^\[" .claude/hooks/workflow/dry_run.log)
PASSED=$(grep -c "^\[PASS\]" .claude/hooks/workflow/dry_run.log)
FAILED=$(grep -c "^\[FAIL\]" .claude/hooks/workflow/dry_run.log)
SKIPPED=$(grep -c "^\[SKIP\]" .claude/hooks/workflow/dry_run.log)
echo "Total:   $TOTAL"
echo "Passed:  $PASSED"
echo "Failed:  $FAILED"
echo "Skipped: $SKIPPED"
echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "RESULT: ALL TESTS PASSED"
else
  echo "RESULT: $FAILED TEST(S) FAILED"
  echo ""
  echo "Failed tests:"
  grep "^\[FAIL\]" .claude/hooks/workflow/dry_run.log
fi
echo ""
echo "Full log: .claude/hooks/workflow/dry_run.log"
```

---

## Cleanup

Reset state after dry run:

```bash
python3 -c "
import json
from pathlib import Path
Path('.claude/hooks/workflow/state.json').write_text(json.dumps({'workflow_active': False, 'sessions': {}}, indent=2))
print('State reset')
"
rm -rf .claude/sessions/SK-DRY
```

---

## Expected Phase Flow

```
/implement SK-DRY  →  pre-coding  (Test 1)
    ↓
/code              →  code        (Test 3)
    ↓
/code-review       →  review      (Test 6)
    ↓
/commit            →  final-commit (Test 9)
    ↓
/create-pr         →  create-pr   (Test 9)
    ↓
/validate          →  validate    (Test 9)
    ↓
/push              →  push        (Test 9)
```

## Quick Reference

| Exit Code | Meaning |
|-----------|---------|
| 0 | Allow / pass-through |
| 2 | Block (message shown to user) |

| Guard | Blocks When |
|-------|-------------|
| `phase_guard.py` | Wrong phase predecessor, hold=true, blocked_until_phase set |
| `hold_checker.py` | hold=true or status=aborted (Agent/Skill only) |
| `bash_guard.py` | gh pr create/close/merge/edit, git push outside designated phase |
| `stop_guard.py` | Status != completed or PR not created |
| `decision_guard.py` | /decision not invoked before reviewer stops |
| `validation_loop.py` | Confidence score below threshold (70) |
