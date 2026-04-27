# Refactor `claude-3PO/scripts/` for Abstraction & Reusability

## Context

`claude-3PO/scripts/` is a live workflow-guardrail system (~35 source files, 697 tests) that prevents Claude from drifting during orchestrated phases. Exploration surfaced five concrete problems:

- **Duplication**: `_basenames()` exists verbatim in 4 files; subprocess/git/claude invocations are copy-pasted between `auto_commit.py` and `summarize_prompt.py`; `load_ledger`/`save_ledger` reimplements `lib/file_manager.py`; `REVIEW_PHASES` is defined in two files.
- **Leaky constants**: hardcoded paths (`COMMIT_BATCH_PATH`, `E2E_TEST_REPORT`, `STALE_THRESHOLD_MINUTES`) and magic strings (`"## Specifications"`) are scattered across guardrails/utils instead of living in `constants/`.
- **Long functions**: six functions violate the 15-line rule (validator, resolver, write_guard, auto_commit).
- **Module single-responsibility violations**: several modules do more than one job. `AgentReportGuard` extracts bullets (`_extract_bullet_items` l.79-84), writes specs to disk (`_auto_write_specs` l.153-168), calls `Recorder.record_*` directly (l.226,232-234), and mutates state (`_mark_specs_agent_failed` l.210-213) — a guard should only validate. `PhaseGuard` calls `Resolver.auto_start_next()` inline (l.109,114,129,134) — resolution leaking into validation. `TaskCreatedGuard` mutates state via `add_created_task`/`add_subtask` (l.57,79-83). `Recorder` calls `AgentReportGuard.scores_valid`/`verdict_valid` (l.173) — validation thresholds leaking into recording. A `extract_section_map` pattern is duplicated in `write_guard.py:104-105` and `agent_report_guard.py:99` and belongs in extractors.
- **Unused/drifting Pydantic models**: `models/state.py` is defined but almost never used; `StateStore` reads/writes raw dicts. Worse, the model schema has **already drifted** from the real stored shape (`PlanReview` is singular in the model but stored as `list[dict]`). A straight migration would fail validation on existing `state.jsonl` snapshots.

Goal: improve abstractions and reusability without breaking the live `state.jsonl` format or the 697-test suite. TDD throughout (per `CLAUDE.md`).

## Approach — 6 staged PRs, each independently green

Each stage ends with all tests passing. Stages are ordered smallest-blast-radius first so that the Pydantic stage touches *already-centralized* code.

### Stage 1 — Centralize pure helpers

Extract the 4× duplicated `_basenames()` and the path-match helpers (`_is_plan_file`, `_is_contracts_file`, `_check_report_path`) into new `utils/paths.py`.

- **Touch**: new `utils/paths.py`; `utils/recorder.py:38`, `guardrails/agent_guard.py:70`, `guardrails/edit_guard.py:89`, `utils/resolver.py:173`, `guardrails/write_guard.py:80-89,204-206`; new `tests/test_paths.py`.
- **TDD**: write `test_paths.py` first (parametrized across abs/rel paths, `.md`/`.json`, plan-vs-contracts). Then extract. Then replace call-sites one at a time.
- **Risk**: one of the four `_basenames` copies may differ subtly — diff byte-for-byte before unifying; if divergent, keep named variants.

### Stage 2 — Constants & config caching

Single source for `REVIEW_PHASES`, the `"## Specifications"` marker, `COMMIT_BATCH_PATH`, `E2E_TEST_REPORT`, `STALE_THRESHOLD_MINUTES`. Cache `Config()` via `functools.lru_cache`.

- **Touch**: new `constants/paths.py`, `constants/phases.py`, `constants/markers.py`; `guardrails/phase_guard.py:13-20`, `dispatchers/subagent_stop.py:28-32`, `utils/auto_commit.py:21,35`, `guardrails/write_guard.py:19,127`; `config/__init__.py` adds `get_config()`.
- **TDD**: `test_config_cache.py` asserts `get_config() is get_config()`; revise existing guard tests to import from new locations.
- **Risk**: cached Config breaks tests that mutate it — expose `cache_clear()` and call from `conftest.py` `config` fixture.

### Stage 3 — Subprocess + ledger I/O unification

New `lib/shell.py` owns `run_git(...)` and `invoke_claude(...)`. `auto_commit.py` stops re-implementing JSON I/O and routes ledger reads/writes through `lib/file_manager.py`.

- **Touch**: new `lib/shell.py`; `utils/auto_commit.py:43-62,106-138,200-214`, `utils/summarize_prompt.py:41-50`; new `tests/test_shell.py`.
- **TDD**: `test_shell.py` with `subprocess.run` mocked (non-zero exit, timeout, empty stdout). Revise `test_auto_commit.py` and `test_summarize_prompt.py` to patch `lib.shell.*` instead of `subprocess.run`.
- **Risk**: `FileManager` locking differs from current ad-hoc ledger — keep `FileManager(..., lock=True)` and rerun concurrency tests.

### Stage 4 — Slim long functions + recorder dispatch map

Split every >15-line function: `validator.py:418-437,468-492`, `resolver.py:388-408`, `auto_commit.py:243-254,257-273`, `write_guard.py:98-118,126-144`. Replace `recorder.py`'s if/elif tree (line 199+) with `TOOL_RECORDERS: dict[str, Callable]` dispatch map.

- **TDD**: existing coverage is strong (`test_validators.py`, `test_resolvers.py`, `test_recorders.py`, `test_auto_commit.py`). Add micro-tests for each extracted helper; add `test_recorder_dispatch.py` parametrizing every tool name.
- **Verification**: ad-hoc AST lint asserting max 15 lines per `FunctionDef` in touched files.
- **Risk**: recorder branches have ordering assumptions — preserve insertion order in the dispatch map; add a snapshot test against a recorded live-session state.

### Stage 5 — Module single-responsibility enforcement

Every module does exactly one job. Guards validate. Extractors parse. Recorders mutate state. Resolvers decide phase completion. Dispatchers route. Today these are blurred — this stage unblurs them.

Two goals bundled because they share the same mechanical surgery (move functions, update imports, adjust tests):

**5a. Break cross-layer imports**
- Extract score/verdict threshold logic from `AgentReportGuard` into `lib/scoring.py` (used by both the guard and the recorder).
- Extract parallel-explore check from `Resolver` into `lib/parallel_check.py` (used by `PhaseGuard`).
- After: `guardrails/*` does not import `utils/*`; `utils/recorder.py` does not import `guardrails/*`.

**5b. Move leaked responsibilities to their rightful modules**

| Code | From | To |
|---|---|---|
| `_extract_bullet_items()` | `guardrails/agent_report_guard.py:79-84` | `lib/extractors.py` |
| `_auto_write_specs()` spec file writing | `guardrails/agent_report_guard.py:153-168` | `utils/recorder.py` (call after guard passes, from `dispatchers/subagent_stop.py`) |
| `recorder.record_scores/verdict/revision_files()` calls inside `validate()` | `guardrails/agent_report_guard.py:226,232-234` | `dispatchers/post_tool_use.py` / `subagent_stop.py` (dispatchers call guard, then recorder) |
| `_mark_specs_agent_failed()` state mutation | `guardrails/agent_report_guard.py:210-213` | `utils/recorder.py` |
| `Resolver.auto_start_next()` calls inside guard | `guardrails/phase_guard.py:109,114,129,134` | `dispatchers/post_tool_use.py` (post-validation step) |
| `state.add_created_task()` / `add_subtask()` mutations | `guardrails/task_created_guard.py:57,79-83` | `utils/recorder.py` |
| `{name.strip(): body for name, body in sections}` pattern | `guardrails/write_guard.py:104-105`, `agent_report_guard.py:99` | new `extract_section_map()` in `lib/extractors.py` |
| Threshold validation (`scores_valid`, `verdict_valid`) | `guardrails/agent_report_guard.py` (still called from `utils/recorder.py:173`) | `lib/scoring.py` (covered by 5a) |

- **TDD**: existing `test_specs_agent_report_guard.py`, `test_resolvers.py`, `test_recorder.py`, `test_task_created.py`, `test_auto_transition.py` cover behavior. Add `test_scoring.py`, `test_parallel_check.py` importing new locations. For each moved function, add a focused unit test at the destination *before* moving, so the move is a green-to-green transition.
- **Verification**:
  - AST check — no `guardrails/*` imports `utils.*`; no `utils/recorder.py` imports `guardrails.*`.
  - Grep invariants — no `self.state.set_*`, `self.state.add_*`, `self.state.mark_*` calls inside `guardrails/*`.
  - Grep invariants — no regex/markdown parsing helpers defined inside `guardrails/*` (must import from `lib/extractors.py`).
  - Full suite green.
- **Risk**: dispatchers must now call guard → recorder → resolver in the correct order; getting the order wrong changes observable behavior. **Mitigation**: add a dispatcher-level integration test per hook (`test_pre_tool_use_flow.py`, `test_subagent_stop_flow.py`) asserting the exact call sequence via mocks before any code moves. Also: `AgentReportGuard` currently writes specs files *during* validation; moving this to the recorder means the file doesn't land until after guard returns Allow — verify no downstream code (violations log, resolver) reads those files mid-validation.

### Stage 6 — Pydantic adoption (pragmatic middle ground)

**Scope flag**: the user picked "Full refactor including models". Straight full adoption is unsafe because `models/state.py` has drifted from the real stored shape, and `state.jsonl` snapshots from live workflows must still load. Three-tier approach instead:

1. **Fix the schema drift** in `models/state.py`: `plan.review` → `plan.reviews: list[PlanReview]` (same for `CodeReview`); add `status`/`verdict` fields to match actual storage; add `ConfigDict(extra="allow")` so unknown keys (`agent_rejections`, `docs`, `created_tasks`) don't fail.
2. **Pydantic at the boundary**: new `StateStore.load_model() -> State` / `save_model(State)`; existing `load`/`save`/`update` stay dict-shaped for backwards compatibility. Callers opt in.
3. **Convert ad-hoc dicts** we already touched: `validator.py:_new_item` (line 504-515) → `StoryItem`; `auto_commit.py` batch entries (line 243-254) → `BatchEntry`. Leave `recorder`/`resolver` on dict access for now.

- **Touch**: `models/state.py`; new `models/batch.py`, `models/story.py`; `lib/state_store.py`; `utils/initializer.py:31-108` (build `State(...).model_dump()` instead of raw dict).
- **TDD**: **migration test first** — `test_state_roundtrip.py` loads fixtures under `tests/fixtures/state_snapshots/` (copy the current `state.jsonl` into fixtures) and asserts `State.model_validate(d).model_dump(exclude_unset=False) == d` modulo defaults. This test drives the schema fixes. Then revise `test_initializer.py`, add `test_state_store_model.py`.
- **Verification**: every line of the current `state.jsonl` validates under `State`; existing 697 tests green.
- **Risk**: `model_dump()` may reorder keys vs. hand-built dicts, changing byte-level output. Use `model_dump(exclude_none=False, by_alias=False)` and add a canonical key-order test.

## Critical files

- `claude-3PO/scripts/utils/recorder.py` (touched in stages 1, 4, 5)
- `claude-3PO/scripts/utils/auto_commit.py` (touched in stages 2, 3, 4)
- `claude-3PO/scripts/utils/validator.py` (touched in stages 4, 6)
- `claude-3PO/scripts/guardrails/write_guard.py` (touched in stages 1, 2, 4)
- `claude-3PO/scripts/lib/state_store.py` (stage 6)
- `claude-3PO/scripts/models/state.py` (stage 6 — schema drift fix)

## Existing utilities to reuse (don't rebuild)

- `lib/file_manager.py:22-62` — `load_file`/`save_file`/`update_file` with lock support; replaces custom ledger I/O in Stage 3.
- `lib/extractors.py` — full set of markdown/score/verdict parsers already exist; add domain grouping rather than reimplementing.
- `lib/hook.py` — stdin/stdout protocol, already used by all dispatchers.

## README updates

- `claude-3PO/scripts/README.md` — update module table when `utils/paths.py`, `lib/shell.py`, `lib/scoring.py`, `lib/parallel_check.py`, and new `constants/*.py` files land (per `CLAUDE.md` rule to update the in-scope README).

## Verification plan (per stage)

1. `cd claude-3PO/scripts/tests && python3 -m pytest` — 697 existing tests green.
2. Stage-specific grep invariants (one `REVIEW_PHASES`, one `_basenames`, no `guardrails/` → `utils/` imports, etc.).
3. Stage 6: every line of live `state.jsonl` validates via `State.model_validate_json(line)`.
4. Smoke test on a throw-away workflow run (`/build` or `/specs`) to confirm hooks still fire correctly — the 697-test suite is mostly unit/integration with tmp state files; one live run catches protocol regressions.

## Out of scope

- Test coverage for `lib/archiver.py`, `lib/injector.py`, `lib/parser.py`, `dispatchers/pre_tool_use.py`, `post_tool_use.py` (adds risk without being required by the refactor). Flag separately.
- Converting `recorder.py`/`resolver.py` to full Pydantic — deferred behind the boundary-only migration.
- Re-architecting the `State` phase model to remove hardcoded phase property accessors.
