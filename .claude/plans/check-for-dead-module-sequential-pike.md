# Dead Modules & Dead Code in `claude-3PO/scripts/`

## Context

The refactor branch split several large modules (state_store, handlers) and moved `guardrails/`, `headless/` under `handlers/`. Some pre-split modules and the newly-relocated `headless/` tree now have orphan code — defined but never imported by anything outside tests. The goal is to find and remove that dead weight so `scripts/` only ships what's actually wired into hooks or callers.

Dead = no inbound imports from production code (dispatchers, handlers, utils, lib) and not an entry point referenced in `claude-3PO/hooks/hooks.json`. Tests-only usage is listed separately because deleting the module means the test goes too.

## Findings

### 1. `handlers/headless/reviewer.py` — entire file dead (and broken)

- Defines `invoke_reviewer(self, agent_name, review_type)` at module scope but with a `self` parameter — not a method, not a class.
- Grep: zero inbound imports anywhere in `claude-3PO/` (only self-reference at `handlers/headless/reviewer.py:17`).
- Imports `lib.shell.invoke_headless_agent` (which *is* used by `utils/auto_commit.py:33` and `utils/summarize_prompt.py:22`, so the lib helper stays).

### 2. `handlers/headless/prompts/` — dead prompt templates

- `handlers/headless/prompts/claude/plan_review.md`
- `handlers/headless/prompts/codex/plan_review.md`
- Only consumer is the dead `reviewer.py` docstring (`reviewer.py:3`). No other grep hits.

### 3. `lib/injector.py` — module unused

- Grep for `injector`, `inject_into`, `inject_frontmatter` across `scripts/` returns only the file itself and a stale README entry (`scripts/README.md:148`).
- Imports `lib.extractors.extract_md_body` and `StateStore` but nobody imports back from it.

### 4. `lib/parallel_check.py` — only tests use it (orphaned predicate)

- `is_parallel_explore_research()` is imported by `tests/test_parallel_check.py:5` and referenced nowhere in production.
- README (`scripts/README.md:154`) claims it is "shared by the recorder, resolver, and guard" — false today. Either the callers were removed in refactor (bug) or the predicate was never wired in. Needs a call with the user.

### 5. `scripts/README.md` — drift

- Lists `headless/codex/codex_plan_review.py` and `headless/claude/claude_plan_review.py` (`README.md:198-199`) — these paths don't exist. The current file is `handlers/headless/reviewer.py`.
- Lists `injector.py` and `parallel_check.py` under active helpers — both are dead.
- Lists `clarity-review.md` template — `lib/clarity_check.py` IS still used (good), but the template path needs confirming.

### Not dead (verified)

- `constants/constants.py` — re-exported via `constants/__init__.py:3` (`from .constants import *`); its `CODE_EXTENSIONS`, `COMMANDS_MAP`, `SPECS_*` are used across guardrails.
- `config/config.py` — `Config` class re-exported via `config/__init__.py:5`; `get_config()` is the widely-used accessor.
- `lib/clarity_check.py` — used by `utils/initializer.py:21` and `utils/hooks/post_tool_use.py:8`.
- `lib/shell.invoke_headless_agent` — used by `utils/auto_commit.py`, `utils/summarize_prompt.py`.

## Recommended Actions

**High confidence — safe to delete:**

1. Delete `claude-3PO/scripts/handlers/headless/reviewer.py`.
2. Delete `claude-3PO/scripts/handlers/headless/prompts/` (recursively).
3. Delete `claude-3PO/scripts/handlers/headless/` itself if it becomes empty.
4. Delete `claude-3PO/scripts/lib/injector.py`.

**Needs user decision (see AskUserQuestion below):**

5. `lib/parallel_check.py` + `tests/test_parallel_check.py` — delete the pair, or rewire the predicate into `phase_guard.py` / `utils/recorder.py` / `utils/resolver.py` as the README claims.

**README (`claude-3PO/scripts/README.md`):**

6. Remove the two `headless/claude/` and `headless/codex/` bullets (`README.md:198-199`).
7. Remove `injector.py` row from the lib table (`README.md:148`).
8. Remove or update `parallel_check.py` row (`README.md:154`) based on the decision on action 5.

## Critical Files

- `claude-3PO/scripts/handlers/headless/reviewer.py` — delete
- `claude-3PO/scripts/handlers/headless/prompts/claude/plan_review.md` — delete
- `claude-3PO/scripts/handlers/headless/prompts/codex/plan_review.md` — delete
- `claude-3PO/scripts/lib/injector.py` — delete
- `claude-3PO/scripts/lib/parallel_check.py` — delete or rewire
- `claude-3PO/scripts/tests/test_parallel_check.py` — delete if module deleted
- `claude-3PO/scripts/README.md` — trim stale rows

## Verification

1. `source /home/emhar/claude-3PO/.venv/bin/activate`
2. From `claude-3PO/scripts/`: `python -m pytest` — expect green (the deleted modules had no production callers, and matching tests are removed in the same change).
3. Grep sweep: `grep -rn "injector\|parallel_check\|handlers.headless\|invoke_reviewer" claude-3PO/scripts/ claude-3PO/hooks/` — should return no hits after deletions.
4. Spot-check `hooks.json` still resolves to existing dispatcher files.
