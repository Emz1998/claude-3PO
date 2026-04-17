# project_manager

Local JSON-based backlog management with optional GitHub Projects (v2) sync. Day-to-day work reads and writes a single file — `issues/backlog.json` — with no GitHub API calls. Sync is a separate subcommand that pushes data to GitHub when needed.

## Layout

```
project_manager/
├── __init__.py              # Exposes ProjectManager, Syncer
├── cli.py                   # argparse wrapper — entry point
├── manager.py               # ProjectManager: list/view/update/add/progress/unblocked
├── sync.py                  # Syncer: push backlog.json → GitHub Issues & Projects v2
├── config.py                # Project, repo, owner, project number, data paths
├── issues/
│   └── backlog.json         # Single backlog file (stories with nested tasks)
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

Lists items whose `blocked_by` dependencies are all `Done` (or have no dependencies). Only considers items with status `Backlog` or `Ready`.

```bash
# All unblocked items
python -m project_manager.cli unblocked

# Narrow to one story
python -m project_manager.cli unblocked --story SK-001

# Promote unblocked Backlog items to Ready
python -m project_manager.cli unblocked --promote

# JSON output
python -m project_manager.cli unblocked --json
```

### sync

Syncs `backlog.json` to GitHub Issues and GitHub Projects (v2). Requires the `gh` CLI authenticated. Defaults come from `config.py`.

```bash
# Sync everything
python -m project_manager.cli sync

# Preview without writing
python -m project_manager.cli sync --dry-run

# Sync only stories or only tasks
python -m project_manager.cli sync --sync-scope stories
python -m project_manager.cli sync --sync-scope tasks

# Override config values
python -m project_manager.cli sync --repo owner/repo --project 5 --owner owner

# Close all issues and remove them from the project
python -m project_manager.cli sync --delete-all
python -m project_manager.cli sync --delete-all --dry-run
```

The sync runs in passes: resolve/create issues, add to project, batch field updates, set parent-child relationships, and set blocking relationships (via `addBlockedBy` GraphQL mutations).

---

## config.py

Project settings live in `project_manager/config.py` as module constants:

```python
PROJECT = "Claude-3PO"
REPO = "Emz1998/claude-3PO"
OWNER = "Emz1998"
PROJECT_NUMBER = 4

DATA_PATHS = {
    "backlog": str(_BASE / "issues" / "backlog.json"),
}
```

Override per-invocation with `--repo`, `--project`, and `--owner` on the `sync` subcommand.

---

## Data structure

All data lives in a single `issues/backlog.json` file. Stories sit at the top level; tasks are nested under each story.

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
          "is_blocking": ["T-002"],
          "blocked_by": [],
          "acceptance_criteria": ["…"],
          "milestone": "v0.1.0",
          "issue_number": 433
        }
      ]
    }
  ]
}
```

`issue_number` is populated by `sync` after the corresponding GitHub issue is created, and is reused on subsequent syncs.

#### Statuses: `Backlog` · `Ready` · `In progress` · `In review` · `Done`
#### Priorities: `P0` · `P1` · `P2` · `P3`
#### Complexity: `XS` · `S` · `M` · `L` · `XL`

---

## Tests

```bash
pytest claude-3PO/project_manager/tests
```

`test_manager.py` / `test_cli.py` cover local backlog operations; `test_sync.py` covers sync logic with mocked `gh`; `test_sync_e2e.py` is the end-to-end suite.
