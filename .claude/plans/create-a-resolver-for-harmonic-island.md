# Plan — Diff Pass 2 against remote state to stop rebroadcasting unchanged fields

## Context

Every watcher cycle currently re-sends every field on every item in Pass 2
regardless of what actually changed:

- `~77` `updateProjectV2ItemFieldValue` mutations in 3 batched GraphQL
  calls (Status + Priority + Start date + Target date + Points/Complexity,
  × 21 items) via `_collect_mutations` → `run_pass2_batched`.
- `21` separate `gh issue edit --milestone …` subprocess invocations via
  `_apply_issue_level_parallel` → `_issue_level_edit`. Each is a fresh
  `gh` boot + OAuth handshake (~200–500 ms). Parallelism with
  `MAX_WORKERS` only shaves so much.

GitHub accepts the redundant writes silently (no "already taken" errors
like `addBlockedBy` produced before the last fix), so the cost has been
invisible — but on a backlog this size a re-sync where *nothing semantic
changed* still burns 5–10 s of wall-clock time and 20+ API calls.

**Goal:** before Pass 2 mutates, build a `{item_id: {field_name:
current_value}}` map from state we already have in memory, and emit a
mutation only when the in-memory value differs from the remote value.
Same for milestone in `_issue_level_edit`: skip the `gh issue edit`
subprocess when the remote issue's milestone already matches.

Target outcomes:

- No-op re-sync (status-flip cycle from the watcher's own writeback):
  Pass 2 sends **0 field mutations and 0 `gh issue edit` calls**.
- Single-status change: ~**1 field mutation, 0 subprocess calls**.
- First sync on a fresh project: identical behaviour to today (every
  field differs from the empty remote → every mutation emitted).

## Approach

The prior fixes (concurrent-sync lock, `addBlockedBy` edge-diff) already
established the pattern: *fetch remote state once up-front, pass it
through to the mutation builder, filter pairs that already match*. The
same pattern applies here.

Two independent diff points:

1. **Project-field diff (the big one).** Extend `get_project_items` so
   the returned dicts carry their current Project v2 field values.
   `gh project item-list --format json` already emits them as top-level
   keys (`status`, `priority`, `points`, `complexity`, `start date`,
   `target date`) alongside `id` and `content` — we just haven't parsed
   them. Pipe that `remote_values` map into `_mutations_for_item` and
   skip any field whose normalized remote value equals the in-memory
   value. **Net round-trips added: 0** — we already make this call.
2. **Milestone diff.** Extend `_gh_issue_list` to include milestone in
   its `--json` selection. Plumb the resulting `{issue_number:
   milestone}` map into `_issue_level_edit` so it skips the
   `gh issue edit --milestone` subprocess when the remote value already
   matches. **Net round-trips added: 0** — same `gh issue list` call,
   one extra field in the `--json` projection.

Fallback (if `gh project item-list` on the installed CLI version turns
out *not* to emit field values alongside `id`/`content`): replace that
call with a `gh api graphql` query that selects
`items(first: 200){ nodes { id, content { ...on Issue{number,title} },
fieldValues(first: 20){ nodes { ...on ProjectV2ItemFieldSingleSelectValue
{ name field { ...on ProjectV2FieldCommon{name} } } ... } } } }`. Still
one call, still no net round-trips added — just a swap.

## Files

### Edits

- **`claude-3PO/project_manager/sync.py`**
  - `get_project_items` (line 556): return items as today, but annotate
    each with a parsed `field_values: dict[str, Any]` key so downstream
    code doesn't have to re-guess the CLI's schema. Add a small parser
    `_extract_item_field_values(raw_item) -> dict[str, Any]` that pulls
    the known keys (`"status"`, `"priority"`, `"points"`,
    `"complexity"`, `"start date"`, `"target date"`) out of the raw
    `gh project item-list` entry and normalizes them. Keep the 15-line
    cap by splitting a `_normalize_field_value(name, raw)` helper that
    handles the date / number / string variants.
  - `_build_remote_values_map(items)` — returns
    `{item_id: {field_name: current_value}}` keyed by the canonical
    field names (`"Status"`, `"Priority"`, `"Points"`, `"Complexity"`,
    `"Start date"`, `"Target date"`) so the map lines up with the
    mutation builder's `_BASE_FIELD_SPECS`.
  - `_mutations_for_item` (line 743): accept a new
    `remote_values: dict[str, Any]` argument (the inner map for this
    item's `item_id`); before appending a mutation, compare
    `_normalize_field_value(field_name, raw)` with the remote value and
    `continue` when they match. Print a concise "skip" log so the
    dropped writes are visible during debugging, matching the
    `addBlockedBy` "already blocked by … — skipped" pattern.
  - `_collect_mutations` (line 765): accept `remote_by_item` (the outer
    map); look up `remote_by_item.get(item_id, {})` per task and pass
    through.
  - `run_pass2_batched` (line 917): accept `remote_by_item`, thread to
    `_collect_mutations`. Also thread a `remote_milestones:
    dict[int, str]` to the issue-level edit path (next bullet).
  - `_issue_level_edit` (line 892): accept `remote_milestone: str |
    None`; skip the `gh issue edit --milestone` branch when it equals
    `task.get("milestone")`. Still run `set_parent_issue` and
    `create_branch_for_issue` (those paths are already noop-safe — GH
    sub-issue POST is idempotent, `gh issue develop` is guarded by
    branch name).
  - `_apply_issue_level_parallel` (line 907): take `remote_milestones`,
    pass the per-task value through to `_issue_level_edit`.
  - `Syncer._run_remote_passes` (line 1262): after
    `get_project_items(...)`, call `_build_remote_values_map(items)` and
    pass it to `run_pass2_batched`. The milestone map comes from
    extending `fetch_all_open_issues_full` (next bullet).
  - `_gh_issue_list` (line 60) / `fetch_all_open_issues_full` (line 76):
    include `milestone` in `--json` so the resulting dicts carry
    `{"milestone": {"title": "..."}}`. Add a thin
    `build_issue_milestone_map(issues) -> dict[int, str]` helper.
  - `Syncer._ensure_all_issues` (line 1252): already calls
    `fetch_all_open_issues` — switch the ultimate caller path to use
    `fetch_all_open_issues_full` once and derive both
    `{title: number}` (what it uses today) *and* `{number: milestone}`
    from the same response. Thread the milestone map into `sync()` so
    `_run_remote_passes` can forward it.
  - All new/edited functions stay ≤ 15 lines per CLAUDE.md.

### Tests

- **`claude-3PO/project_manager/tests/test_sync.py`**
  - Extend **`TestCollectMutations`**: existing tests now pass an empty
    `remote_by_item={}` to lock in the default "no remote info → emit
    everything" behaviour.
  - New class **`TestPass2Diffing`** covering:
    - `test_skips_field_when_value_unchanged` — remote has `status:
      "In progress"`, item has `status: "In progress"` → no mutation
      emitted; `test_emits_mutation_when_status_changes` — remote
      differs → mutation emitted; both exercise `_mutations_for_item`
      directly, not through network.
    - `test_normalizes_dates_before_comparing` — remote date
      `"2026-02-17"` vs in-memory `"2026-02-17"` ⇒ skipped even if one
      side came in with trailing `T00:00:00Z` (belt-and-braces against
      the CLI's occasional ISO timestamp variant).
    - `test_story_vs_task_field_diff_independent` — flips Points on a
      story while Complexity stays; asserts exactly one mutation is
      emitted and it's the Points one.
    - `test_all_fields_match_emits_zero_mutations` — the no-op re-sync
      case; the watcher's own writeback must not re-broadcast anything.
  - New class **`TestIssueLevelDiff`**:
    - `test_skips_gh_edit_when_milestone_matches` — patches
      `sp.run`; asserts it's not called when remote milestone ==
      `task["milestone"]`.
    - `test_runs_gh_edit_when_milestone_differs` — same harness,
      opposite assertion.
  - New class **`TestExtractItemFieldValues`** covers the CLI-output
    parser for the three raw shapes (single-select, number, date) so
    a future `gh` version bump surfaces as a unit-test failure, not a
    silent re-broadcast regression.
  - **`TestRunPass2Batched`** (if one doesn't exist, add a small one):
    integration-style — mocks `_fetch_project_field_values` equivalents
    and `subprocess.run`, exercises a 21-item fixture where 20 items
    fully match remote and 1 has a single status change; asserts
    exactly one mutation batch with one mutation + zero `gh issue edit`
    calls.

- **`claude-3PO/project_manager/tests/test_sync_e2e.py`** — no edit.
  The e2e suite exercises a throwaway project end-to-end and will
  automatically validate that the diff doesn't accidentally drop real
  changes on the first-time sync path.

### Docs

- **`claude-3PO/project_manager/README.md`** — brief note in the
  "watch" / auto-resolve section: "Pass 2 now skips field updates whose
  remote value already matches the in-memory value, so a no-op re-sync
  (the watcher echoing its own writeback) issues zero field mutations
  and zero `gh issue edit` calls."

## Reused / existing code

- The `addBlockedBy` edge-diff in `_blocking_mutations` (sync.py:294) is
  the template for the field diff — same "fetch once up front, filter in
  the builder, print a `— skipped` line" shape.
- `_build_field_value` (sync.py:700) / `_BASE_FIELD_SPECS` (sync.py:715)
  already canonicalise the in-memory → GraphQL-value direction; the new
  normalizer only needs to cover the reverse direction for compare.
- `fetch_all_open_issues_full` (sync.py:76) already exists and is used
  elsewhere — we just extend its `--json` projection.
- `find_item_id` (sync.py:589) is untouched; the diff lookup happens
  after `item_id` is resolved, using the same id as the mutation key.

## Verification

1. **Unit tests.** `pytest claude-3PO/project_manager/tests/test_sync.py
   -v` — new `TestPass2Diffing`, `TestIssueLevelDiff`,
   `TestExtractItemFieldValues`, and extended `TestCollectMutations` all
   green; pre-existing sync tests unchanged.
2. **Full suite regression.** `pytest claude-3PO/project_manager/tests/
   --ignore=claude-3PO/project_manager/tests/test_sync_e2e.py` — 229+
   tests green, no new failures.
3. **Manual smoke with the watcher.**
   ```
   python -m project_manager.cli watch --backlog-path /tmp/pj.json
   ```
   - Seed `/tmp/pj.json` with the real backlog, save once → expect the
     usual Pass 2 output (first sync populates everything).
   - Save the file unchanged (or touch it) → expect:
     `Pass 2 ... No field updates to send.` and `Setting issue-level
     fields (parallel)...` prints only `— skipped (milestone
     unchanged)` lines, zero `gh issue edit` subprocesses.
   - Flip one status (e.g. `SK-001: Backlog → In progress`) → expect
     exactly one field mutation in the batch summary and one
     per-item `✓ … [In progress]` line.
4. **Wall-clock check.** `time` the second save on the watcher — expect
   the second cycle to finish in ~1–2 s vs ~8–15 s today.

## Out of scope (defer)

- **Pass 3 sub-issue diff.** `set_parent_issue` calls the REST sub-issue
  POST which already errors idempotently on a duplicate; we don't need
  to pre-fetch them. Revisit if that endpoint ever starts returning a
  hard failure like `addBlockedBy` did.
- **Labels / assignees / title / body diff on the issue itself.** Those
  aren't written by the current sync's Pass 2 path at all — `gh issue
  edit` is only invoked for milestone — so there's nothing to diff yet.
- **Batching `get_project_items` + `fetch_all_open_issues_full` into a
  single GraphQL call.** Tempting (it would merge two of the three
  pre-Pass-2 round-trips into one), but cross-cuts the flat-data /
  project-data separation in the module and isn't required to hit the
  goal. Revisit if we ever add more remote lookups in the pre-pass.
- **Cache the `fetched` remote snapshot across watcher cycles.** Would
  drop the pre-Pass-2 fetches to zero on an idle-but-frequent watcher,
  but invalidation (what if someone edits on GitHub?) is a whole
  separate discussion.
