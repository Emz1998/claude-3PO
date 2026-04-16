---
name: test-specs
description: Live E2E test of specs workflow guardrails
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, Agent, WebFetch, AskUserQuestion
model: haiku
---

You are a **guardrail test runner**. Systematically test every guardrail by deliberately doing wrong things first (which MUST be blocked), then doing the correct thing to advance.

## Reset

!`rm -f "${CLAUDE_PLUGIN_ROOT}/E2E_SPECS_TEST_REPORT.md" "${CLAUDE_PLUGIN_ROOT}/logs/violations.md" "${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl"`

## Workflow Initialization

!`python3 '${CLAUDE_PLUGIN_ROOT}/scripts/utils/initializer.py' specs ${CLAUDE_SESSION_ID} --test test guardrails`

## Rules

- When you get blocked, that is the **expected** outcome. Record it as PASS.
- If a step marked "should block" is NOT blocked, record it as FAIL.
- All subagents must exit immediately — no real work. Every agent prompt: "Do not read any files. Respond with exactly: ..." followed by the required output format.
- After each phase, read `state.jsonl` for your session and compare against the expected JSON. Record mismatches as FAIL.
- After each phase that has blocks, read `${CLAUDE_PLUGIN_ROOT}/logs/violations.md` and verify each block produced a violation entry. Record missing entries as FAIL.
- Write results to `${CLAUDE_PLUGIN_ROOT}/E2E_SPECS_TEST_REPORT.md` after each phase. This file is always writable in test mode.
- The state file is at: `'${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl'`
- The violations log is at: `${CLAUDE_PLUGIN_ROOT}/logs/violations.md`
- **IMPORTANT**: If you are completely blocked, use `/continue` to skip the blocked phase.
- **IMPORTANT**: If bugs are found, write it in the E2E_SPECS_TEST_REPORT.md file. Do not try to fix them.
- **IMPORTANT**: Your role is to test, report and document the bugs, not to fix them.
- **IMPORTANT**: `test-specs` is only triggered by the user. Start with `vision` phase.

## Report Format

Present three tables at the end:

**Guardrail Tests:**

```
| Phase | Step | Expected | Actual | Result |
|-------|------|----------|--------|--------|
```

**State Verification:**

```
| Phase | Check | Expected | Actual | Result |
|-------|-------|----------|--------|--------|
```

**Violations Log:**

```
| Phase | Tool | Action | Logged | Result |
|-------|------|--------|--------|--------|
```

For each block that occurred, verify a matching row exists in `${CLAUDE_PLUGIN_ROOT}/logs/violations.md` with the correct Phase, Tool, and Action. Mark PASS if found, FAIL if missing.

---

**IMPORTANT**: Make sure to read the file first before editing it.
**IMPORTANT**: Write report after each phase.

## Phase: vision

1. `Write` to `random-file.py` — _should block_ (docs-write phase, only docs path allowed)
2. `Edit` on any file — _should block_ (docs-write phase, no edits)
3. `Agent` with `subagent_type: "Research"` — _should block_ (wrong agent for vision phase)
4. `Agent` with `subagent_type: "Architect"` — _should block_ (wrong agent for vision phase)
5. Invoke `/vision`
6. `AskUserQuestion` with question: "What is the name of your project and who is building it?" — _should allow_
7. **Skip remaining 9 questions**: `Edit` on `${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl` — _should allow_ (state.jsonl edit allowed in test mode). No actual state change needed — just verify the escape hatch works.
8. Read the product vision template at `${CLAUDE_PLUGIN_ROOT}/skills/visionize/templates/product-vision.md`
9. `Write` to `projects/docs/product-vision.md` with a valid product vision using dummy answers — _should allow_

**State check:**

```json
{
  "phases": [
    { "name": "vision", "status": "completed" }
  ],
  "docs": {
    "product_vision": { "written": true, "path": "projects/docs/product-vision.md" }
  }
}
```

**Violations check:** Read `${CLAUDE_PLUGIN_ROOT}/logs/violations.md`. Verify these entries exist:

```markdown
| ... | vision | Write | random-file.py | ... |
| ... | vision | Edit | ... | ... |
| ... | vision | Agent | Research | ... |
| ... | vision | Agent | Architect | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: strategy

1. `/decision` — _should block_ (must complete strategy first, cannot skip ahead)
2. `/vision` — _should block_ (cannot go backwards)
3. Invoke `/strategy`
4. `Write` to anything — _should block_ (read-only phase)
5. `Agent` with `subagent_type: "Explore"` — _should block_ (wrong agent for strategy)
6. `Agent` with `subagent_type: "Research"`, prompt: "Do not read any files. Respond with exactly: Done." — _should allow_
7. Invoke 2 more Research agents (total 3) with same prompt — _should allow_
8. `Agent` with `subagent_type: "Research"`, prompt: "Done." — _should block_ (4th Research exceeds max of 3)
9. Wait for all agents to complete

**State check:**

```json
{
  "phases": [
    { "name": "vision", "status": "completed" },
    { "name": "strategy", "status": "completed" }
  ],
  "agents": "3 Research (completed)"
}
```

**Violations check:**

```markdown
| ... | decision | Skill | decision | ... |
| ... | vision | Skill | vision | ... |
| ... | strategy | Write | ... | ... |
| ... | strategy | Agent | Explore | ... |
| ... | strategy | Agent | Research | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: decision

1. Invoke `/decision`
2. `Agent` with `subagent_type: "Architect"` — _should block_ (wrong agent for decision)
3. `AskUserQuestion` with question: "Which programming language and framework will you use for the backend?" — _should allow_
4. **Skip remaining 9 questions**: `Edit` on `${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl` — _should allow_ (state.jsonl edit allowed in test mode). No actual state change needed.
5. `Write` to `projects/docs/decisions.md` with valid decisions using dummy answers — _should allow_

**State check:**

```json
{
  "phases": [
    { "name": "decision", "status": "completed" }
  ],
  "docs": {
    "decisions": { "written": true, "path": "projects/docs/decisions.md" }
  }
}
```

**Violations check:**

```markdown
| ... | decision | Agent | Architect | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: architect

1. Invoke `/architect`
2. `Write` to anything — _should block_ (read-only phase, auto-write only)
3. `Agent` with `subagent_type: "ProductOwner"` — _should block_ (wrong agent for architect)
4. `Agent` with `subagent_type: "Architect"`, prompt with **invalid** architecture (missing sections): "# Bad Architecture\n\nNo structure." — _should block_ at SubagentStop (validation fails)
5. `Agent` with `subagent_type: "Architect"`, prompt with **valid** architecture matching template — _should allow_ and auto-write to `projects/docs/architecture.md`

**State check:**

```json
{
  "phases": [
    { "name": "architect", "status": "completed" }
  ],
  "docs": {
    "architecture": { "written": true, "path": "projects/docs/architecture.md" }
  }
}
```

**Violations check:**

```markdown
| ... | architect | Write | ... | ... |
| ... | architect | Agent | ProductOwner | ... |
```

**IMPORTANT**: Write report after this phase.

## Phase: backlog

1. Invoke `/backlog`
2. `Write` to anything — _should block_ (read-only phase, auto-write only)
3. `Agent` with `subagent_type: "Architect"` — _should block_ (wrong agent for backlog)
4. `Agent` with `subagent_type: "ProductOwner"`, prompt with **invalid** backlog (no stories): "# Bad Backlog\n\nNo stories." — _should block_ at SubagentStop (validation fails)
5. `Agent` with `subagent_type: "ProductOwner"`, prompt with **valid** backlog matching template — _should allow_ and auto-write to `projects/docs/backlog.md` and `projects/docs/backlog.json`

**State check:**

```json
{
  "phases": [
    { "name": "backlog", "status": "completed" }
  ],
  "docs": {
    "backlog": { "written": true, "md_path": "projects/docs/backlog.md", "json_path": "projects/docs/backlog.json" }
  },
  "status": "completed",
  "workflow_active": false
}
```

**Violations check:**

```markdown
| ... | backlog | Write | ... | ... |
| ... | backlog | Agent | Architect | ... |
```

**IMPORTANT**: Write report after this phase.

## Stop hook

After backlog completes, the workflow should be marked as completed. Verify:
- `status` is `"completed"`
- `workflow_active` is `false`
- All 5 phases are completed
- All docs are written

---

## Final Report

1. Present all three tables (Guardrail Tests + State Verification + Violations Log). Count totals.
2. Clean up test files in `projects/docs/`.

If all pass: **All specs guardrails verified.**
If any fail: **GUARDRAIL FAILURES DETECTED — investigate before using in production.**
