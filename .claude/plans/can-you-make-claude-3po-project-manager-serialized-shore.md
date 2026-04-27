# Plan: Two-way sync for `claude-3PO/project_manager/` (pull from GitHub Project)

## Context

`project_manager` is currently one-way: `project.json` → GitHub Project (issues + project fields + milestones + parent-child + blocking edges), wired through `sync.py` and driven by `watcher.py` on file changes. The user wants the reverse direction — GitHub Project → `project.json` — primarily to **bootstrap a fresh `project.json` from an existing GitHub Project**, and to reconcile field-value drift when someone edits the board in the GitHub UI.

Scope (decided with user):
- **Trigger**: runs automatically on **watcher startup** (one-shot pull before the file observer begins), and is also exposed as a manual `pm pull` CLI command for ad-hoc reconciliation. It does **not** run on every file-change event inside the live watch loop.
- **Field scope for existing matched items**: only pull back `Status`, `Priority`, `Points`, `Complexity`, `Start date`, `Target date`, `milestone`. Skip title/description/labels/assignees (local is canonical for text).
- **New GitHub issues** (no matching `issue_number` in `project.json`): import as new stories/tasks. For these, title/description/labels/assignees/fields are all read from GitHub (otherwise the imported entry is empty).
- **Conflict rule**: remote wins for pulled fields.

## Approach

Add a new `importer.py` module alongside `sync.py`, plus a `pm pull` CLI command. Reuse existing sync.py helpers for GitHub Project reads — no new gh-CLI wrappers.

Two code paths inside `Importer.import_from_github(backlog)`:
1. **Reconcile**: for each remote item whose `content.number` matches an `issue_number` already in `project.json`, overwrite the pulled fields only.
2. **Import**: for remote items with no local match, construct a new story or task:
   - Classify story vs task by field presence: `Points` set → story; `Complexity` set → task. Fallback: treat as story (top-level) if ambiguous.
   - Parse ID from title (sync writes titles as `"SK-001: Foo"`); if title lacks an ID prefix, generate the next `SK-NNN` / `T-NNN`.
   - Parse body into `description` + `acceptance_criteria[]` by splitting on `## Acceptance Criteria` (inverse of `sync.build_issue_body` at `sync.py:38`).
   - Parent-child: fetch sub-issue relationships via `gh api /repos/{owner}/{repo}/issues/{num}/sub_issues` (REST) to determine `parent_story_id` for tasks, then nest under the correct story.
   - Capture `labels`, `assignees`, `milestone` from `gh issue list --json` output for newly imported items (single batched call, reuse pattern from `sync.build_issue_milestone_map` at `sync.py:84`).

Remote → local field mapping reuses `sync._REMOTE_RAW_KEYS` (`sync.py:771`) and `sync._extract_item_field_values` (`sync.py:814`) so both directions share one source of truth.

## Files

**Create**
- `claude-3PO/project_manager/importer.py` — `Importer` class + small pure helpers (each ≤15 lines per CLAUDE.md rules).
- `claude-3PO/project_manager/tests/test_importer.py` — unit tests, written first (TDD).

**Modify**
- `claude-3PO/project_manager/cli.py` — register `pull` subcommand (mirror `sync`'s shape at ~`cli.py:120`).
- `claude-3PO/project_manager/manager.py` — add `pull()` method on `ProjectManager` that loads backlog, calls `Importer.import_from_github()`, saves backlog. Wire into `run()` dispatcher (~`manager.py:858`).
- `claude-3PO/project_manager/watcher.py` — in the startup path (before `Observer.start()` at ~`watcher.py:370`), call `ProjectManager.pull()` once. After the pull writes `project.json`, recompute the file hash and seed `self._last_hash` so the observer treats the initial write as its own echo and doesn't trigger an immediate redundant push. Guard with a `--no-pull` CLI flag on `pm watch` for users who want to skip it in a pinch.
- `claude-3PO/project_manager/__init__.py` — export `Importer`.
- `claude-3PO/project_manager/README.md` — document `pm pull` + the watcher startup behavior (required per CLAUDE.md "Identify the README and update it").

## Key functions in `importer.py` (all ≤15 lines, Google-style docstrings)

- `fetch_github_state(repo, owner, project_number)` — returns `{items, fields, milestones, sub_issue_map}`. Reuses `sync.get_project_items`, `sync.get_project_fields`, `sync.build_issue_milestone_map`.
- `index_local_by_issue_number(backlog)` — `{issue_number: (story_ref, task_ref_or_None)}`.
- `parse_id_from_title(title)` — regex `^([A-Z]+-\d+):\s*(.*)$` → `(id_or_None, clean_title)`.
- `parse_body(body)` — split on `## Acceptance Criteria`, return `(description, [criteria_strings])`.
- `classify_item(field_values)` — `"story"` if `points` present, `"task"` if `complexity` present, else `"story"`.
- `next_id(existing_ids, prefix)` — `max(int suffix) + 1` formatted `{prefix}-{NNN}`.
- `update_existing(local_item, remote_field_values, remote_milestone)` — overwrite only pulled fields.
- `build_story_from_remote(...)` / `build_task_from_remote(...)` — construct new dicts matching `SAMPLE_BACKLOG` shape (`tests/test_sync.py:26`).
- `fetch_sub_issues(repo, issue_num)` — `gh api repos/{repo}/issues/{num}/sub_issues` via `utils.gh_utils.gh_json`.
- `Importer.import_from_github(backlog)` — orchestrator; mutates and returns backlog.

## Tests (write before implementation)

Pure logic, no real gh calls — mock via `@patch.object(importer_module, "fetch_github_state", ...)` (same pattern as `tests/test_sync.py:278`).

1. `test_parse_id_from_title` — `"SK-001: Build login"` → `("SK-001", "Build login")`; `"random title"` → `(None, "random title")`.
2. `test_parse_body_roundtrip` — body produced by `sync.build_issue_body` parses back to the original `(description, acceptance_criteria)`.
3. `test_classify_item` — points-only → story; complexity-only → task; neither → story.
4. `test_next_id` — `["SK-001", "SK-003"]` with prefix `SK` → `"SK-004"`; empty → `"SK-001"`.
5. `test_update_existing_overwrites_only_pulled_fields` — local item with custom title/description keeps them; status/priority change to remote values.
6. `test_build_story_from_remote` — mocked remote item produces a dict with every expected key (id, title, description, points, priority, status, acceptance_criteria, issue_number…).
7. `test_import_bootstrap_empty_backlog` — empty backlog + 3 mocked remote items (2 stories, 1 task with sub-issue link) → backlog has 2 stories, story-2 contains 1 task with correct `parent_story_id`.
8. `test_import_reconcile_existing` — backlog with 2 items whose `issue_number` matches remote; remote has different status — local status updated, counts unchanged, no new entries added.
9. `test_import_generates_ids_when_title_has_no_prefix` — remote title `"Fix bug"` → local ID `SK-NNN` auto-generated from existing max.
10. `test_watcher_pulls_on_startup` — patch `ProjectManager.pull` + `Observer`; construct watcher, call its startup entry; assert `pull` ran exactly once **before** `Observer.start()` and that `_last_hash` was seeded from the post-pull file bytes (no spurious push on first event).
11. `test_watcher_no_pull_flag_skips_pull` — with `--no-pull`, `ProjectManager.pull` is never called.

## Verification

1. `cd claude-3PO/project_manager && pytest tests/test_importer.py -v` — all new tests pass.
2. `pytest tests/ -v` — no regression in `test_sync.py`, `test_manager.py`, `test_cli.py`, `test_watcher.py`.
3. Manual bootstrap e2e:
   - Back up current `project.json`.
   - Replace with minimal skeleton (`{"project": "Claude-3PO", "goal": "...", "stories": []}`).
   - Run `python -m claude-3PO.project_manager.cli pull`.
   - Diff output against backup — all stories/tasks restored with matching statuses/fields.
4. Manual reconcile e2e:
   - Edit one item's Status on the GitHub board UI.
   - Run `pm pull`.
   - Confirm `project.json` picks up the change; re-run `pm sync` is a no-op (no outbound drift).
5. Watcher-startup e2e:
   - Edit an item's Status on the GitHub UI.
   - Start `pm watch`.
   - Confirm logs show a pull ran before observer startup, `project.json` reflects the remote change, and no extra push fires from the seed write (hash dedup holds).
