# Plan: Stop syncing tasks to GitHub issues; drop blocking fields from tasks

## Context

Today, `project_manager` syncs both stories AND tasks as separate GitHub issues:
parent/child sub-issue links, blocking relationships, project field updates,
the works. Tasks also carry `blocked_by`/`is_blocking` fields that drive the
`unblocked` CLI command, the auto-promote resolver rule, and a dedicated sync
pass.

We're collapsing the model so only **stories** represent units of GitHub work.
Tasks remain in `project.json` as local-only sub-items (still flattened for the
`list`/`view` table; still gated on parent-story status by the resolver), but
they no longer touch GitHub and no longer carry blocking fields. Stories keep
their `blocked_by`/`is_blocking` and the corresponding sync pass.

User will manually close existing task issues on GitHub.

## Decisions

- Stories keep `blocked_by`/`is_blocking`; tasks lose them.
- Tasks lose `issue_number` from `project.json` too (decoupled from GitHub).
- `--sync-scope` flag is removed entirely (only stories sync now).
- `unblocked` CLI lists stories only.
- Pass 3 (`_apply_parent_child`) is removed entirely.
- Resolver code is unchanged: `is_unblocked([], …)` already returns True, so
  tasks without `blocked_by` still get auto-promoted Backlog→Ready when their
  parent story leaves Backlog (parent-story gate still applies).

## Files to modify

### `claude-3PO/project_manager/project.json`
- For every task under `stories[*].tasks`: remove `blocked_by`,
  `is_blocking`, and `issue_number` keys.
- Stories keep all fields.

### `claude-3PO/project_manager/manager.py`
- `_base_item_fields()` (L123-138): drop `blocked_by` from the returned dict
  — it's now story-only.
- `_normalize_story()` (L141-149): add `"blocked_by": story.get("blocked_by", [])`.
- `_normalize_task()` (L152-162): no `blocked_by` field.
- `_view_ready_tasks()` (L427-441): drop the `_is_unblocked(...)` check; just
  filter by `parent_id == key` and `status in ACTIVE_STATUSES`.
- `_filter_unblocked_tasks()` (L684-701): **delete**.
- `_task_unblocked_json()` (L715-720): **delete**.
- `_unblocked_to_json()` (L723-726): simplify to `[_story_unblocked_json(s) for s in stories]`.
- `_print_unblocked_list()` (L736-745): drop `task_pairs` parameter.
- `_promote_unblocked_in_place()` (L755-763): drop the `task_pairs` loop.
- `_new_item_defaults()` (L771-778): split into two helpers — the story
  default keeps `is_blocking`/`blocked_by`, the task default drops them.
  Update both call sites in the add-story / add-task builders.
- The `unblocked` command handler in `ProjectManager.run` dispatch (search
  for the `"unblocked"` mode): stop computing/passing task pairs.

### `claude-3PO/project_manager/sync.py`
- `_apply_sync_scope()` (L1250-1257): **delete**.
- `_collect_blocking_pairs()` (L244-258): unchanged signature, but caller
  now passes only stories.
- `_apply_parent_child()` and the helpers `_fetch_rest_ids_parallel`,
  `_post_sub_issue` if used solely by Pass 3 (verify): **delete**.
- `Syncer.sync()` (L1474-1486): drop `sync_scope` kwarg; load only stories
  for sync purposes (still load tasks for the writeback file structure, but
  don't pass them to issue passes); update print line.
- `_ensure_all_issues()` (L1544-1559): only loop over stories; drop the
  `(stories, tasks)` tuple iteration.
- `_run_remote_passes()` (L1561-1588): pass `stories` (not `all_items`) to
  project-batched add and to Pass 4; remove the Pass 3 call.
- `save_flat_data()` (L224-236): only writeback story `issue_number`s; do
  not iterate `story.tasks`.
- `_clear_issue_numbers()` (L1230s): only clear stories' `issue_number`.

### `claude-3PO/project_manager/cli.py`
- Remove `_add_sync_parser` `--sync-scope` argument (L134-137).
- Update `_EPILOG` examples (L25-26): drop `unblocked` examples if they
  reference task behavior; keep one story-level example.
- `_add_unblocked_parser` (L145-149): unchanged on the surface; help text
  may need a tweak ("List **stories** whose dependencies are Done").

### `claude-3PO/project_manager/README.md`
- "sync" section: drop `--sync-scope` docs and Pass 3 / task-issue text.
- "unblocked" section: clarify it operates on stories only.
- "Data Structure" example: remove `blocked_by`/`is_blocking`/`issue_number`
  from the nested task example.
- Auto-resolve rules: keep Rule A but note it's parent-status-gated for
  tasks (no blocker gate on tasks anymore).

### Tests (TDD — update tests **before** the implementation)
- `tests/test_manager.py`: remove `is_blocking`/`blocked_by` from task
  fixtures (L38-109 area); update `test_unblocked` and `test_unblocked_json`
  to assert stories-only output; update `test_view_ready_tasks` to not
  rely on blocker filtering.
- `tests/test_sync.py`: remove task fixtures' `issue_number`/blocking
  fields; in `TestBlockingRelationships` keep only story-pair tests; remove
  `--sync-scope tasks` cases; remove sub-issue / parent-child tests.
- `tests/test_sync_e2e.py`: same fixture cleanup; assert that tasks aren't
  registered as issues end-to-end.
- `tests/test_resolver.py`: keep story blocker cascade tests; drop tests
  that exercise `task_blocked_by_*`; verify the parent-status gate still
  promotes tasks correctly without a `blocked_by` field.
- `tests/test_cli.py`: remove `--sync-scope` test cases.
- `tests/test_watcher.py`: minor fixture cleanup.

## Verification

1. `pytest claude-3PO/project_manager/tests/ -x` — full suite passes after
   tests are updated.
2. `python -m project_manager.cli list` — table renders; tasks present.
3. `python -m project_manager.cli view SK-001 --ready-tasks` — lists ready
   tasks under SK-001 without blocker filtering.
4. `python -m project_manager.cli unblocked --json` — output contains only
   `type: "story"` entries.
5. `python -m project_manager.cli sync --dry-run` — log shows stories only;
   no "tasks" pass; no Pass 3 line; Pass 4 only mentions story pairs.
6. `python -m project_manager.cli add-task --parent-story-id SK-001 --title "Smoke test"`
   — new task in `project.json` has no `blocked_by`/`is_blocking`/`issue_number`.
7. `git diff project.json` — only stories retain blocking fields and
   `issue_number`; tasks are stripped.
