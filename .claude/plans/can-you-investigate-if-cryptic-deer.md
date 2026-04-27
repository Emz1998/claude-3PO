# Close Guardrail Coverage Gaps Per Phase

## Context

The user asked whether every phase/skill invocation in `claude-3PO/` triggers a guardrail, and — if not — wants a plan to close the gaps.

**Short answer:** every *Skill invocation* is already guarded (PreToolUse → `Skill` matcher → `phase_guard` enforces ordering/workflow/exhaustion for every slash-command). Same for every `Agent`, `Bash`, `WebFetch`, `TaskCreate`, `AskUserQuestion` invocation — each has a dedicated guard in `TOOL_GUARDS` at `scripts/handlers/guardrails/__init__.py:163-172`.

**The actual gap is not at invocation time — it's at *write/edit time within a phase*.** Three phases have `docs_write`/`code_edit` capability but no phase-specific path/content rules in `FileWriteGuard.validate()` / `FileEditGuard.validate()`: they currently fall through to a generic "allow" after the writable-phase check, so any file under any path is permitted.

Closing these gaps gives the system the same "write only where the phase says you can" guarantee it already gives the other write phases (`plan`, `write-tests`, `write-code`, `write-report`, `plan-review`, `test-review`, `code-review`).

## Confirmed Inventory

| Layer | Phase | Status |
|---|---|---|
| `phase_guard` (Skill) | all 22 phases | ✅ covered |
| `agent_guard` (Agent) | all agent phases | ✅ covered |
| `command_guard` (Bash) | all phases via whitelist | ✅ covered |
| `agent_report_guard` (SubagentStop) | plan-review, code-review, test-review, tests-review, quality-check, validate, architect, backlog | ✅ covered via `SCORE_PHASES` / `VERDICT_PHASES` / `SPECS_PHASES` at `agent_report_guard.py:52-54` |
| `agent_report_guard` | strategy, explore, research, plan | ⚠️ free-form outputs — *intentional* (lean) |
| `write_guard` | `vision` (docs_write) | ❌ **gap** — no path check |
| `write_guard` | `decision` (docs_write) | ❌ **gap** — no path check |
| `write_guard` | `refactor` (code_write) | ⚠️ unscoped — intentional? |
| `edit_guard` | `plan-revision` (code_edit) | ❌ **gap** — no path/section check |
| `edit_guard` | `refactor` (code_edit) | ⚠️ unscoped — intentional? |

## Recommended Changes (TDD, lean)

### 1. `scripts/handlers/guardrails/write_guard.py`

Add two ≤15-line methods that mirror `check_report_path()`:

- `check_vision_path()` — assert `path_matches(self.file_path, self.config.product_vision_file_path)`; raise `ValueError` on mismatch.
- `check_decision_path()` — assert `path_matches(self.file_path, self.config.decisions_file_path)`; raise `ValueError` on mismatch.

Wire both into `validate()` dispatch (after the existing `elif self.phase == "write-report":` branch):

```python
elif self.phase == "vision":   self.check_vision_path()
elif self.phase == "decision": self.check_decision_path()
```

No content-schema check — `vision`'s structural validation already lives in the `visionize` skill's own `pre_tool_use.py` hook; `decision`'s output is a 10-Q&A write-up with no canonical template.

### 2. `scripts/handlers/guardrails/edit_guard.py`

Add `validate_plan_revision()` — identical to existing `validate_plan_review()` (path check + section-preservation check), because `plan-revision` is a sub-phase of `plan-review` targeting the same plan file (per `commands/plan-review.md:31,37`).

Wire into `validate()`:

```python
elif self.phase == "plan-revision": self.validate_plan_revision()
```

### 3. `scripts/handlers/guardrails/agent_report_guard.py`

**No change.** My initial exploration claimed `quality-check` / `validate` / `architect` / `backlog` were unguarded; reading `agent_report_guard.py:52-54` confirms they are covered via `VERDICT_PHASES` and `SPECS_PHASES`.

### 4. `refactor` phase — decision pending

Config declares `"workflows": []` — refactor is a standalone escape-hatch. Either:
- **(a)** leave unscoped (current behaviour; generic `check_writable_phase`/`check_editable_phase` still gates entry), or
- **(b)** restrict refactor edits to a config-driven whitelist.

Pending user confirmation.

### 5. Tests (write first)

Add to `scripts/tests/test_file_guard.py` (mirror existing parametrized style, use `make_hook_input` + shared `config`/`state` fixtures from `conftest.py`):

- `TestWriteVisionPhase` — allow `product_vision_file_path`; block other paths; block when phase is not `vision`.
- `TestWriteDecisionPhase` — allow `decisions_file_path`; block other paths.
- `TestEditPlanRevision` — allow plan file; block non-plan paths; block edits that remove required sections.

Run the guardrail test suite (`scripts/tests/test_file_guard.py`, `test_guardrails.py`, `test_specs_agent_report_guard.py`) to confirm no regression.

## Critical Files

- `claude-3PO/scripts/handlers/guardrails/write_guard.py` (add 2 methods + 2 dispatch lines)
- `claude-3PO/scripts/handlers/guardrails/edit_guard.py` (add 1 method + 1 dispatch line)
- `claude-3PO/scripts/tests/test_file_guard.py` (add 3 test classes)
- `claude-3PO/scripts/config/config.py:542,552` (existing `product_vision_file_path`, `decisions_file_path` properties — reused, not modified)

## Verification

1. `pytest claude-3PO/scripts/tests/test_file_guard.py -v` — new tests green, existing tests still green.
2. `pytest claude-3PO/scripts/tests/ -v` — full suite green.
3. Manual smoke: simulate `vision` phase writing to wrong path → block; `decision` phase writing to wrong path → block; `plan-revision` edit dropping `## Tasks` section → block.

## READMEs to update

- `claude-3PO/scripts/handlers/guardrails/README.md` (if present) — add the newly-covered phases to the coverage table.

## Out of Scope

- Adding structural validators for `decision.md` or `refactor` scoping (needs separate design).
- Re-plumbing `strategy`/`explore`/`research` report validation (their outputs are free-form notes consumed by downstream phases, not schema-validated artifacts).
