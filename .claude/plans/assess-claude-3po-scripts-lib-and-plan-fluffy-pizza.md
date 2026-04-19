# Consolidate `claude-3PO/scripts/lib/`

## Context

`claude-3PO/scripts/lib/` currently holds 14 modules (~2100 LOC). Several are thin shells with a single caller, and `extractors.py` (635 LOC, 25+ functions) is the opposite problem — one file doing five jobs. The user finds the layout over-modularized, which both obscures the module-single-responsibility rule and makes navigation harder.

Goal: shrink lib/ from **14 → 8 modules** while *strengthening* SRP (split `extractors.py` into domains, inline modules that only had one caller, merge modules that share a job).

## Confirmed decisions

1. Deep restructure.
2. Merge `scoring.py` + `specs_validation.py` → `validators.py`.
3. Keep `injector.py` as-is (WIP, 0 callers today).
4. Inline `parser.py` + `archiver.py` into `utils/initializer.py` (only non-test caller).

## Final layout

```
lib/
  __init__.py
  extractors/                       # package, __init__ re-exports public names
    __init__.py
    hooks.py                        # strip_namespace, extract_skill_name, extract_agent_name
    review.py                       # extract_scores, extract_verdict (+ helpers)
    markdown.py                     # md sections, tables, bullets, bold metadata
    plans.py                        # plan dependencies/tasks/files_to_modify
    commands.py                     # extract_build_instructions, extract_ci_status
  validators.py                     # merged scoring.py + specs_validation.py
  subprocess_agents.py              # merged shell.py + clarity_check.py
  json_store.py                     # renamed file_manager.py
  paths.py                          # unchanged
  hook.py                           # unchanged (11 callers)
  violations.py                     # unchanged (5 callers)
  injector.py                       # unchanged (WIP)
  state_store/                      # unchanged
```

**Removed/moved:** `parser.py`, `archiver.py` → `utils/initializer.py`. `parallel_check.py` → deleted (0 production callers). `ordering.py` → inlined into `handlers/guardrails/phase_guard.py` (its only caller). `scoring.py` + `specs_validation.py` → `validators.py`. `shell.py` + `clarity_check.py` → `subprocess_agents.py`. `file_manager.py` → renamed `json_store.py`.

**Why `paths.py` stays standalone:** it's filesystem-path semantics, distinct job from string extraction; already SRP-clean with 5 legitimate callers.

## Critical files to modify

- `claude-3PO/scripts/lib/extractors.py` — split into the `extractors/` package
- `claude-3PO/scripts/utils/initializer.py` — absorbs parser + archiver content; update its own imports
- `claude-3PO/scripts/handlers/guardrails/phase_guard.py:13` — inline `validate_order` from `lib.ordering`
- `claude-3PO/scripts/lib/shell.py` — becomes `subprocess_agents.py`, absorbs clarity_check
- Callers of renamed modules: `auto_commit` (file_manager → json_store), 4× specs_validation callers, 4× scoring callers, 4× shell callers, 3× clarity_check callers
- Extractors callers (18 files): **no edits needed** — `extractors/__init__.py` re-exports existing public names

## Migration order (safe steps)

1. **Independent merges** (each is self-contained): scoring + specs_validation → validators.py; shell + clarity_check → subprocess_agents.py; rename file_manager → json_store. Update callers in the same change.
2. **Inline single-caller modules**: parser + archiver → initializer.py; ordering → phase_guard.py.
3. **Split extractors**: create `extractors/` package with 5 sub-modules; add `__init__.py` re-exports so no caller changes.
4. **Delete** `parallel_check.py` + `test_parallel_check.py` last, after grep confirms no remaining reference.

## TDD — tests first (per CLAUDE.md)

- `test_scoring.py` + `test_specs_validator.py` → merge to `test_validators.py` (already exists; reconcile)
- `test_shell.py` + `test_clarity_check.py` → merge to `test_subprocess_agents.py`
- `test_parser.py` + `test_archiver.py` → merge into `test_initializer.py`
- `test_auto_commit.py` → update `lib.file_manager` import → `lib.json_store`
- `test_extractors.py` → optionally split per sub-domain; or keep single file (re-exports make it valid either way)
- `test_phase_guard.py` → absorb `test_ordering.py` cases; delete `test_ordering.py`
- `test_parallel_check.py` → delete

For each merge, write/revise the combined test file first, run it (expect failures), then perform the merge and re-run until green.

## Verification

1. `pytest claude-3PO/scripts/tests/` — full suite green.
2. Grep for deleted module names (`parallel_check`, `lib.ordering`, `lib.parser`, `lib.archiver`, `lib.file_manager`, `lib.shell`, `lib.clarity_check`, `lib.scoring`, `lib.specs_validation`) across `claude-3PO/` — expect zero hits outside of `logs/` and historical markdown.
3. Run a representative hook end-to-end (e.g. `pre_tool_use` dispatcher with a sample payload) to confirm no import-time regressions.
4. Update `claude-3PO/scripts/README.md` lib/ section to reflect the new 8-module layout.
