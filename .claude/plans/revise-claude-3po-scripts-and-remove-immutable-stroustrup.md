# Trim claude-3PO/scripts/ workflow to a 7-phase MVP

## Context

The implement workflow currently has 13 phases. The six review/delivery phases —
`plan-review`, `tests-review`, `validate`, `code-review`, `pr-create`, `ci-check`
— add agent loops, score-based reviews, and PR/CI orchestration that the user no
longer wants. Trim the workflow to a lean MVP:

```
explore → research → plan (checkpoint) → create-tasks → write-tests → write-code → write-report
```

Scope is **scripts/ only**. Per user direction, do not touch
`claude-3PO/commands/*.md`, `claude-3PO/agents/*.md`, or the dead state-model
classes (`PR`, `CI`, `PlanReview`, `CodeReview`, `TestReview`, `quality_check_result`,
`reviews` / `files_to_revise` / `files_revised` lists). Those stay as
forward-compat noise; this plan trims only what `scripts/` references.

After plan completes, the workflow pauses for human review (the `plan` phase
inherits the `checkpoint: true` flag that previously lived on `plan-review`).
`/continue` is the universal advancer.

## Phase 1 — Tests first (TDD)

**Delete entire files** (their suites only target removed phases):
- `tests/test_revise_plan.py`
- `tests/test_plan_approved.py`

**Update**:
- `test_resolvers.py` — drop `TestResolvePlanReview`, `TestResolveTestsReview`,
  `TestResolveValidate`, `TestResolveCodeReview`, `TestResolvePrCreate`,
  `TestResolveCiCheck`. Update `TestAutoAdvanceOnSkipped` to use a different
  phase pair (e.g. `plan` skipped → `create-tasks`).
- `test_state_store.py` — drop `TestPlan::test_add_plan_review` /
  `test_set_last_plan_review_status` / `test_plan_review_count`,
  `TestTests::test_add_test_review` / `test_test_review_count` /
  `test_last_test_review`, `TestCodeFiles::test_add_code_review` /
  `test_set_last_code_review_status` / `test_code_review_count`,
  `TestPR`, `TestCI`, `TestQualityCheck`. Keep the basic facade tests.
- `test_recorders.py` — drop `TestRecordCodeReview`, `TestRecordTestReview`,
  `test_edit_in_plan_review_marks_plan_revised`,
  `test_edit_in_tests_review_records_test_revision`,
  `test_edit_in_code_review_records_file_revision`. Keep Bash/Write/Skill paths.
- `test_guardrails.py` — drop `TestAgentReportGuard`. Keep the reinvoke-completed
  test but switch from `plan` to a non-checkpoint phase. Drop `TestPhaseGuard`
  cases that target review phases.
- `test_validators.py` — drop `TestPlanContentValidation` only the parts that
  reference removed phases; drop `TestIsAgentAllowed` plan/code/test review
  blocks; drop `TestIsAgentReportValid`, `TestValidateReviewSections`. Drop
  `test_pr_create_*` and `test_ci_check_*` from `TestIsCommandAllowed`. Drop
  `test_plan_review_*` and `test_tests_review_*` and `test_code_review_*`
  from `TestIsFileEditAllowed`. Keep plan/write-tests/write-code/write-report
  flows.
- `test_continue.py` — drop `test_continue_force_completes_code_review`,
  `test_continue_force_completes_tests_review`,
  `test_continue_after_code_review_passed`, `test_blocked_for_plan_review`.
  Keep the non-review `/continue` cases (write-code, no-phase block).
- `test_auto_transition.py` — drop
  `test_plan_review_pass_does_not_auto_start_create_tasks`,
  `test_write_code_auto_starts_after_tests_review`. Add a new test:
  `plan` completion should NOT auto-start `create-tasks` (checkpoint pause).
  Update `tests-review` skill-block test to use a different removed-phase
  fixture or drop it.
- `test_runners.py` — drop `TestCheckTests` and `TestCheckCI`; keep
  `TestCheckPhases`. Update `StopGuard` to no longer require tests/CI.
- `test_initializer.py` — drop `parse_skip` cases for `--skip-explore-only`
  variants only if they depend on dropped phases (probably none affected).
- `test_config.py` — update `TestRequiredAgents` to drop `validate_agent` /
  `tests_review_agent`; update `test_implement_phases` to assert the new
  7-phase track; update `test_implement_phases_order` similarly. Drop
  `test_plan_review_agent_count`.
- `test_constants_and_config_cache.py` — `REVIEW_PHASES` becomes empty (or
  the test asserts the constant is empty / removed).
- `test_implement_plan.py` — drop the implement-plan validation tests if they
  rely on the implement plan template still running; check whether plan-phase
  validation still requires those sections (it should — plan stays).

**Keep untouched** (verify after):
- `test_auto_resolver.py`, `test_auto_commit.py`, `test_subprocess_agents.py`
- `test_base_state.py`, `test_implement_state.py`, `test_state_roundtrip.py`
- `test_create_tasks.py`, `test_task_created.py`, `test_task_lifecycle.py`
- `test_extractors.py`, `test_paths.py`, `test_violations.py`,
  `test_pre_tool_violation_phase.py`, `test_subagent_stop_violations.py`

## Phase 2 — Config + constants

- **`config/config.json`** — Remove the six phase entries (plan-review,
  tests-review, validate, code-review, pr-create, ci-check). **Add
  `"checkpoint": true`** to the `plan` entry so the resolver still pauses
  after plan completes. Drop the `score_thresholds` block (now unused).
- **`constants/constants.py`** — Trim `COMMANDS_MAP`: keep only
  `write-tests` and `write-code` (TEST_COMMANDS); delete the
  `tests-review`, `pr-create`, `ci-check` keys.
- **`constants/phases.py`** — `REVIEW_PHASES` becomes empty
  `frozenset()` (kept as a stub for forward-compat consumers).
- **`models/state.py`** — `TDD_PHASES` becomes `("write-tests",)`
  (drop `tests-review`).

## Phase 3 — Resolver

`utils/resolver.py`:

- Delete `_resolve_plan_review`, `_resolve_test_review`, `_resolve_code_review`,
  `_resolve_validate`, `_resolve_pr_create`, `_resolve_ci_check` and their
  shared helpers (`_is_revision_needed`, `_get_pending_scores`,
  `_mark_review_failed`, `_mark_review_passed`, `_resolve_score_review`).
- Empty `_PHASE_RESOLVER_MAP` (or remove the constant + its dispatch).
- `_TOOL_RESOLVER_MAP` — drop `pr-create`, `ci-check`. Keep `plan`,
  `create-tasks`, `write-tests`, `write-code`, `write-report`.
- `_skip_tdd_phases` — only needs to skip `write-tests` now (tests-review
  is gone). Update the loop accordingly.
- `_is_phase_ready_to_advance` — replace the hard-coded
  `plan-review` checkpoint string with `self.config.is_checkpoint_phase(phase)`
  so the new `plan` checkpoint flag drives the pause.

## Phase 4 — Recorder + hooks

- **`utils/recorder.py`** `_dispatch_edit` — drop the `plan-review`,
  `tests-review`, `code-review` branches. Edits happen during `plan` itself
  (reuse the existing `plan-review` revision recording → simplify to record
  the plan as revised when edited during `plan` phase, or just delete since
  there's no review loop to gate).
- **`utils/hooks/subagent_stop.py`** — drop `validate_agent_report` (and
  `apply_report_allow`); `record_agent_completion` is the only remaining
  responsibility. Drop `REVIEW_PHASES` import.

## Phase 5 — Guards

- **`agent_report_guard.py`** — delete the file (no review phases left). Remove
  it from `handlers/guardrails/__init__.py` exports.
- **`phase_guard.py`** —
  - Drop `_EXHAUSTION_MAP`, `is_review_exhausted`.
  - Drop `handle_plan_approved`, `handle_revise_plan`, `handle_reset_plan_review`
    methods and their dispatch in `validate()`.
  - `handle_continue` — drop the special-case that refuses `/continue` for
    `plan-review` (it's gone). `/continue` from `plan` becomes the standard
    advancer.
  - `get_skill_phases` — drop the `tests-review` TDD filter line; no longer
    needed.
- **`agent_guard.py`** — drop `check_plan_revision_done`,
  `check_test_revision_done`, `check_code_revision_done`, `check_revision_done`
  and the call site in `validate()`. Agent gating for `Plan` / `Explore` /
  `Research` stays.
- **`edit_guard.py`** — drop `validate_plan_review`, `validate_test_review`,
  `validate_code_review` and their dispatch. Edit guard now only matters for
  the `plan` phase (preserving sections during plan author edits via the
  existing `check_plan_edit_path` / `check_plan_edit_preserves_sections`
  pair — keep those, route them from the new `plan` phase branch in
  `validate()`).
- **`stop_guard.py`** — drop `check_tests` and `check_ci` (and their imports);
  `check_phases` is the only remaining check. Update the `validate()` checks
  list to just `[self.check_phases]`.
- **`command_validator.py`** — no per-phase `pr-create` / `ci-check`
  branches in code, but the trimmed `COMMANDS_MAP` will naturally drop those
  paths. Verify no exhaustiveness asserts remain.
- **`__init__.py`** — keep all guards still in use; drop
  `agent_report_guard` re-export.

## Phase 6 — Dispatchers

- **`dispatchers/subagent_stop.py`** — drop the
  `state.current_phase == "plan-review"` checkpoint trigger. The new
  checkpoint-on-`plan` is enforced by the resolver alone (no `Hook.discontinue`
  needed; `plan` already pauses because of `checkpoint: true`). Remove the
  `validate_agent_report` call entirely (the helper is gone).

## Phase 7 — Docs + state seed

- **`scripts/README.md`** — update the phase track table to the 7-phase MVP;
  drop the rows in the Guardrails table for `AgentReportGuard`. Drop the
  `subagent_stop.py` review/checkpoint sentence.
- **`scripts/state.json`** — regenerate fresh from `models/state.py` defaults
  (the dead PR/CI/review fields stay in the dump per Pydantic model).

## Critical files to modify

- `/home/emhar/claude-3PO/claude-3PO/scripts/config/config.json`
- `/home/emhar/claude-3PO/claude-3PO/scripts/constants/constants.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/constants/phases.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/models/state.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/utils/resolver.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/utils/recorder.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/utils/hooks/subagent_stop.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/handlers/guardrails/phase_guard.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/handlers/guardrails/agent_guard.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/handlers/guardrails/edit_guard.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/handlers/guardrails/stop_guard.py`
- `/home/emhar/claude-3PO/claude-3PO/scripts/handlers/guardrails/__init__.py` (drop `AgentReportGuard` re-export)
- `/home/emhar/claude-3PO/claude-3PO/scripts/handlers/guardrails/agent_report_guard.py` (delete)
- `/home/emhar/claude-3PO/claude-3PO/scripts/dispatchers/subagent_stop.py`

## Integration risks

1. **Plan checkpoint behavior** — the resolver currently keys checkpoint off
   the literal string `"plan-review"`. Switching to
   `config.is_checkpoint_phase(phase)` is essential or `plan` will auto-advance.
2. **Skill commands left dead** — `/plan-approved`, `/revise-plan`,
   `/reset-plan-review`, `/code-review`, `/pr-create`, `/ci-check`, etc.
   markdown files in `claude-3PO/commands/` continue to exist; invoking them
   will fall through `phase_guard.validate()` and block via the ordering
   check. Acceptable per scope decision.
4. **Dead state fields** — `PR`, `CI`, `quality_check_result`, all `reviews`
   lists and revision-tracking pairs stay in the Pydantic schema. They'll
   serialize as defaults; consumers should ignore them.
5. **`utils/auto_resolver.py`** is a keeper — verify it doesn't reach into
   the removed resolver methods (it shouldn't; it just calls `resolve()`).
6. **`AgentReportGuard` import audit** — grep for any other importer of the
   guard before deleting the module.

## Verification

1. `pytest claude-3PO/scripts/tests --ignore=tests/test_auto_resolver.py` — all green.
2. `python3 -c "import json; json.load(open('claude-3PO/scripts/config/config.json'))"` — parses.
3. `python3 -c "from config import Config; c=Config(); assert c.implement_phases == ['explore','research','plan','create-tasks','write-tests','write-code','write-report']"` — confirms the trimmed track.
4. `python3 -c "from config import Config; c=Config(); assert c.is_checkpoint_phase('plan')"` — confirms the moved checkpoint flag.
5. `grep -rn "plan-review\|tests-review\|code-review\|validate\|pr-create\|ci-check" claude-3PO/scripts/` — only docstring/comment references remain (no code-path references).
6. End-to-end: feed a minimal implement state with `plan` completed through `resolve()`, confirm it does **not** auto-advance to `create-tasks`. Then call `auto_start_next(skip_checkpoint=True)` and confirm `create-tasks` opens.
