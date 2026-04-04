# Constrain Read Guard to CODEBASE.md + Plan Files + Written Files

## Context
The current `read_guard.py` has broad always-allowed lists (extensions like `.json`, `.md`, `.yaml`; prefixes like `.claude/`, `node_modules/`). The user wants to tighten this so that during coding phases, reads are constrained to only three sources:

1. **`CODEBASE.md`** — a project root file containing codebase context (create if it doesn't exist)
2. **Plan-listed files** — files from `## Files to Modify` / `## Critical Files` in the active plan
3. **Previously written files** — files already written/edited during the current session (tracked via `files_written` state key)

## Approach

### Step 1: Create `CODEBASE.md` in project root
Create an empty/stub `CODEBASE.md` at the repo root so it exists for future use.

### Step 2: Rewrite `read_guard.py` to use the three-source constraint
- Remove `ALWAYS_ALLOWED_PREFIXES` and `ALWAYS_ALLOWED_EXTENSIONS` broad allowlists
- Allow reads of `CODEBASE.md` (by filename match)
- Allow reads of plan-listed files (existing `_load_plan_files` logic — keep as-is)
- Allow reads of files in `state["files_written"]` list
- Keep test file allowance during `write-tests` phase

### Step 3: Track all written code files in `write_guard.handle_post()`
Add a `files_written: list[str]` state key. In `handle_post()`, append every successfully written file path to this list (catch-all before the final return).

### Step 4: Initialize `files_written` in workflow initializer
Add `files_written: []` to the initial state alongside `test_files_created`.

### Step 5: Update dry run test cases
- Update existing read guard tests to reflect the new constraint
- Add test: read a previously written file → allowed
- Add test: read `CODEBASE.md` → allowed
- Add test: read a random `.json` file → blocked (no longer always-allowed)

## Files to Modify
| File | Action |
|------|--------|
| `CODEBASE.md` | Create stub file in project root |
| `.claude/hooks/workflow/guards/read_guard.py` | Rewrite validation to three-source constraint |
| `.claude/hooks/workflow/guards/write_guard.py` | Track written files in `files_written` state key |
| `.claude/hooks/workflow/dry_runs/implement_dry_run.py` | Update read guard test cases |
| `.claude/hooks/workflow/utils/workflow_initializer.py` | Add `files_written: []` to initial state |

## Verification
1. Run `python3 .claude/hooks/workflow/dry_runs/implement_dry_run.py --tdd --story-id SK-123` — all tests pass
2. Verify: read `CODEBASE.md` → allowed
3. Verify: read plan-listed file → allowed
4. Verify: read previously written file → allowed
5. Verify: read non-plan, non-written file → blocked
6. Verify: read `.json` file → blocked (no longer always-allowed)
