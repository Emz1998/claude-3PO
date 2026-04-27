# project_manager

Local JSON-based backlog management with optional GitHub Projects (v2) sync. Day-to-day work reads and writes a single file — `project.json` — with no GitHub API calls. Sync is a separate subcommand that pushes data to GitHub when needed.

## Layout

```
project_manager/
├── __init__.py              # Exposes ProjectManager, Syncer
├── cli.py                   # argparse wrapper — entry point
├── manager.py               # ProjectManager: list/view/update/add/progress/unblocked
├── resolver.py              # Pure rule engine: derived status resolution
├── watcher.py               # Foreground watcher: auto-resolve + auto-sync on file edit
├── sync.py                  # Syncer: push project.json → GitHub Issues & Projects v2
├── config.py                # Project, repo, owner, project number, data paths
├── project.json             # Single backlog file (stories with nested tasks)
├── templates/
│   └── issue_view.txt       # Default template for `view` command
├── utils/
│   └── gh_utils.py          # `gh` CLI wrappers (run, gh_json)
└── tests/                   # Unit + e2e tests
```

The entry point is the `cli` module:

```bash
python -m project_manager.cli <command> [options]
```

---

## Commands

### list (alias: `ls`)

```bash
# List everything
python -m project_manager.cli list

# Filter
python -m project_manager.cli list --status "In progress"
python -m project_manager.cli list --priority P0
python -m project_manager.cli list --label bug
python -m project_manager.cli list --complexity M
python -m project_manager.cli list --milestone v0.1.0
python -m project_manager.cli list --assignee alice
python -m project_manager.cli list --type Spike
python -m project_manager.cli list --story SK-001        # tasks under a story

# Sort
python -m project_manager.cli list --sort-by priority
python -m project_manager.cli list -s status --reverse

# Display
python -m project_manager.cli list --wide                # all columns
python -m project_manager.cli list --keys-only           # IDs only
python -m project_manager.cli list --keys-only --keys-format newline
python -m project_manager.cli list --keys-only --keys-format json
python -m project_manager.cli list --json                # full records as JSON
```

### view

```bash
python -m project_manager.cli view SK-001
python -m project_manager.cli view T-017
python -m project_manager.cli view T-017 --raw           # key-value pairs
python -m project_manager.cli view T-017 --template path/to/template.txt
python -m project_manager.cli view SK-001 --tasks        # child tasks only
python -m project_manager.cli view SK-001 --ready-tasks  # unblocked Backlog/Ready children
python -m project_manager.cli view SK-001 --ac           # acceptance criteria only
python -m project_manager.cli view SK-001 --tdd          # TDD flag
python -m project_manager.cli view SK-001 --json
```

Viewing a story also shows its child tasks (unless a narrowing flag is passed). Accepts either the ID (`SK-001`, `T-017`) or the GitHub issue number.

### update

```bash
python -m project_manager.cli update T-017 --status "In progress"
python -m project_manager.cli update SK-001 --priority P1
python -m project_manager.cli update T-017 --complexity L
python -m project_manager.cli update T-017 --title "New title"
python -m project_manager.cli update T-017 --description "Details…"
python -m project_manager.cli update T-017 --start-date 2026-03-01
python -m project_manager.cli update T-017 --target-date 2026-03-15
python -m project_manager.cli update SK-001 --tdd true
```

#### Status transitions

Valid flow: `Backlog → Ready → In progress → In review → Done`

Invalid transitions are blocked by default. Use `--force` to bypass:

```bash
python -m project_manager.cli update T-017 --status Done --force
```

| From        | To                        |
|-------------|---------------------------|
| Backlog     | Ready                     |
| Ready       | In progress, Backlog      |
| In progress | In review, Ready          |
| In review   | Done, In progress         |
| Done        | In progress               |

### add-story

```bash
python -m project_manager.cli add-story --type Spike --title "Research X"
python -m project_manager.cli add-story --type "User Story" --title "User login" --tdd
python -m project_manager.cli add-story --type Tech --title "Setup DB" --points 3 --priority P1
python -m project_manager.cli add-story --type Bug --title "Fix crash" --milestone v0.2.0
```

Types and ID prefixes:

| Type         | Prefix |
|--------------|--------|
| Spike        | `SK-`  |
| Bug          | `BG-`  |
| User Story   | `US-`  |
| Tech / Story | `TS-`  |

### add-task

```bash
python -m project_manager.cli add-task --parent-story-id SK-001 --title "Write tests"
python -m project_manager.cli add-task --parent-story-id SK-001 --title "Write tests" \
  --priority P1 --complexity M --labels test infra
```

Tasks are always assigned ID prefix `T-` and attached to the given parent story.

### summary

```bash
python -m project_manager.cli summary
python -m project_manager.cli summary --group-by priority
python -m project_manager.cli summary -g complexity
```

Groups items by a field and prints count + point totals per group.

### progress

```bash
python -m project_manager.cli progress
```

Shows overall task completion, status distribution, story completion, and per-story task breakdown.

### unblocked

Lists **stories** whose `blocked_by` dependencies are all `Done` (or have no dependencies). Only considers stories with status `Backlog` or `Ready`. Tasks are local-only sub-items and are not surfaced here.

```bash
# All unblocked stories
python -m project_manager.cli unblocked

# Narrow to one story
python -m project_manager.cli unblocked --story SK-001

# Promote unblocked Backlog stories to Ready
python -m project_manager.cli unblocked --promote

# JSON output
python -m project_manager.cli unblocked --json
```

### sync

Syncs **stories** in `project.json` to GitHub Issues and GitHub Projects (v2). Requires the `gh` CLI authenticated. Defaults come from `config.py`. Tasks live only in the local file and are never registered as GitHub issues.

```bash
# Sync stories
python -m project_manager.cli sync

# Preview without writing
python -m project_manager.cli sync --dry-run

# Override config values
python -m project_manager.cli sync --repo owner/repo --project 5 --owner owner

# Close all issues and remove them from the project
python -m project_manager.cli sync --delete-all
python -m project_manager.cli sync --delete-all --dry-run
```

The sync runs in passes: resolve/create issues, add to project, batch field updates, and set blocking relationships (via `addBlockedBy` GraphQL mutations).

Pass 2 diffs the in-memory values against the remote snapshot before
mutating. Pass 2 skips field writes (Status / Priority / Points /
Complexity / Start date / Target date) and the per-issue milestone edit
when the remote value already matches. A no-op re-sync — the common
case when the watcher echoes its own writeback — issues **zero field
mutations and zero `gh issue edit` subprocesses**. The pre-pass
snapshots reuse the existing `gh project item-list`, `gh issue list`,
and node-ID GraphQL calls, so no extra round-trips are added.

### watch

Runs a foreground watcher that makes `project.json` authoritative end-to-end. On every edit — manual, CLI, or programmatic — the watcher debounces for 500 ms, applies the resolver rules, and pushes the result to GitHub Projects via the same pipeline as `sync`.

```bash
# Watch the default project.json in this package
python -m project_manager.cli watch

# Watch a different file (e.g. during smoke tests)
python -m project_manager.cli watch --backlog-path /tmp/project.json

# Override GitHub targets — same semantics as `sync`
python -m project_manager.cli watch --repo owner/repo --project 5 --owner owner
```

The watcher runs in the foreground; stop it with `Ctrl-C`. Self-writes (the watcher saving the file after the resolver mutates it) are deduped by SHA-256, so the push-to-GitHub cycle does not loop.

On launch, the watcher runs one full resolve + sync cycle before blocking on file events. This converges any drift that accrued while the watcher was off (e.g. `project.json` edits made between runs, or a prior sync that crashed mid-cycle). The Pass 2 diff means the no-op case is cheap — two reads, zero writes.

## Auto-resolve & sync

Two rules drive derived statuses. Both are applied to a fixed point on every edit, so cascades resolve in one watcher cycle.

| Rule | Effect |
|------|--------|
| Unblocked & parent Ready+ → Ready | A story in `Backlog` moves to `Ready` when its `blocked_by` are all `Done`. Tasks no longer carry blockers — they auto-promote `Backlog → Ready` once their parent story leaves `Backlog` (i.e. parent is `Ready`, `In progress`, `In review`, or `Done`). Children of a still-`Backlog` story are not advertised as workable. |
| All tasks Done → In review | A story in `In progress` whose every child task is `Done` moves to `In review`. Stories with no tasks are left alone. |

Neither rule can produce a transition that is not in the `VALID_TRANSITIONS` table (e.g. `Ready → In review` never fires automatically). Run the rules without the watcher via `unblocked --promote` for Rule A; Rule B is only applied by `watch`.

---

## config.py

Project settings live in `project_manager/config.py` as module constants:

```python
PROJECT = "Claude-3PO"
REPO = "Emz1998/claude-3PO"
OWNER = "Emz1998"
PROJECT_NUMBER = 4

DATA_PATHS = {
    "backlog": str(_BASE / "project.json"),
}
```

Override per-invocation with `--repo`, `--project`, and `--owner` on the `sync` subcommand.

---

## Data structure

All data lives in a single `project.json` file. Stories sit at the top level; tasks are nested under each story.

```json
{
  "project": "Avaris",
  "goal": "Establish foundational infrastructure and ML pipeline",
  "dates": { "start": "2026-02-17", "end": "2026-03-02" },
  "totalPoints": 23,
  "stories": [
    {
      "id": "SK-001",
      "type": "Spike",
      "milestone": "v0.1.0",
      "labels": ["spike", "research"],
      "title": "Research feature X",
      "description": "…",
      "points": 2,
      "status": "In progress",
      "tdd": true,
      "priority": "P0",
      "is_blocking": ["TS-002"],
      "blocked_by": [],
      "acceptance_criteria": ["Criterion 1"],
      "start_date": "2026-02-17",
      "target_date": "2026-02-21",
      "issue_number": 432,
      "tasks": [
        {
          "id": "T-001",
          "type": "task",
          "labels": ["analysis"],
          "title": "Run analysis",
          "description": "…",
          "status": "In progress",
          "priority": "P0",
          "complexity": "M",
          "acceptance_criteria": ["…"],
          "milestone": "v0.1.0"
        }
      ]
    }
  ]
}
```

`issue_number` is populated on **stories** by `sync` after the corresponding GitHub issue is created, and is reused on subsequent syncs. Tasks never receive an `issue_number` — they are local-only sub-items.

#### Statuses: `Backlog` · `Ready` · `In progress` · `In review` · `Done`
#### Priorities: `P0` · `P1` · `P2` · `P3`
#### Complexity: `XS` · `S` · `M` · `L` · `XL`

---

## Tests

```bash
pytest claude-3PO/project_manager/tests
```

`test_manager.py` / `test_cli.py` cover local backlog operations; `test_sync.py` covers sync logic with mocked `gh`; `test_sync_e2e.py` is the end-to-end suite.
