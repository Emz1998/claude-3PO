# github_project

Local JSON-based project management tool. All data lives in `issues/` — no GitHub API required for day-to-day use. A separate sync script pushes data to GitHub Projects when needed.

## Files

```
github_project/
├── project_manager.py   # Local task/story management (no GitHub dependency)
├── sync_project.py      # Sync local JSON → GitHub Issues & Projects
├── config.yaml          # Repo, owner, project number, and data paths
├── issues/
│   ├── sprint.json      # Current sprint tasks (T-xxx)
│   └── stories.json     # Stories and spikes (SK-xxx, TS-xxx)
└── templates/
    └── issue_view.txt   # Template for `view` command output
```

---

## project_manager.py

Manage tasks and stories locally. All commands read from and write to `issues/sprint.json` and `issues/stories.json`.

### List

```bash
# List all items
python github_project/project_manager.py list

# Filter
python github_project/project_manager.py list --status "In progress"
python github_project/project_manager.py list --priority P0
python github_project/project_manager.py list --label bug
python github_project/project_manager.py list --complexity M
python github_project/project_manager.py list --story SK-001   # tasks under a story

# Sort
python github_project/project_manager.py list --sort-by priority
python github_project/project_manager.py list --sort-by status --reverse

# Display
python github_project/project_manager.py list --wide            # all columns
python github_project/project_manager.py list --keys-only       # comma-separated keys
```

### View

```bash
python github_project/project_manager.py view SK-001
python github_project/project_manager.py view T-017
python github_project/project_manager.py view T-017 --raw       # key-value pairs
python github_project/project_manager.py view T-017 --template path/to/template.txt
```

Viewing a story also shows its child tasks.

### Update

```bash
python github_project/project_manager.py update T-017 --status "In progress"
python github_project/project_manager.py update SK-001 --priority P1
python github_project/project_manager.py update T-017 --complexity L
python github_project/project_manager.py update T-017 --title "New title"
python github_project/project_manager.py update T-017 --start-date 2026-03-01
python github_project/project_manager.py update T-017 --target-date 2026-03-15
python github_project/project_manager.py update SK-001 --tdd true
```

#### Status transitions

Valid flow: `Backlog → Ready → In progress → In review → Done`

Invalid transitions are blocked by default:

```bash
# Blocked — cannot jump from Ready to Done
python github_project/project_manager.py update T-017 --status Done

# Bypass with --force
python github_project/project_manager.py update T-017 --status Done --force
```

Allowed transitions:

| From        | To                        |
|-------------|---------------------------|
| Backlog     | Ready                     |
| Ready       | In progress, Backlog      |
| In progress | In review, Ready          |
| In review   | Done, In progress         |
| Done        | In progress               |

### Add story

```bash
python github_project/project_manager.py add-story --type Spike --title "Research X"
python github_project/project_manager.py add-story --type Tech  --title "Setup DB" --points 3 --priority P1
python github_project/project_manager.py add-story --type Story --title "User login" --tdd
```

Types: `Spike` (prefix `SK-`), `Tech` / `Story` (prefix `TS-`)

### Add task

```bash
python github_project/project_manager.py add-task --parent-story-id SK-001 --title "Write tests"
python github_project/project_manager.py add-task --parent-story-id SK-001 --title "Write tests" \
  --priority P1 --complexity M --labels test infra
```

### Summary

```bash
python github_project/project_manager.py summary
python github_project/project_manager.py summary --group-by priority
python github_project/project_manager.py summary --group-by complexity
```

### Progress

```bash
python github_project/project_manager.py progress
```

Shows overall task completion, status distribution, story completion, and per-story task breakdown.

### Unblocked

Lists items whose `blocked_by` dependencies are all `Done` (or have no dependencies). Only shows items with status `Backlog` or `Ready`.

```bash
# List all unblocked items across the sprint
python github_project/project_manager.py unblocked

# Filter to tasks under a specific story
python github_project/project_manager.py unblocked --story SK-001

# Promote unblocked Backlog items to Ready
python github_project/project_manager.py unblocked --promote

# Combine
python github_project/project_manager.py unblocked --story SK-001 --promote
```

### Create sprint

```bash
python github_project/project_manager.py create-sprint --number 2 --milestone v0.2.0
python github_project/project_manager.py create-sprint --number 2 --milestone v0.2.0 \
  --description "Sprint 2" --due-date 2026-04-01
```

---

## sync_project.py

Syncs local JSON data to GitHub Issues and GitHub Projects (v2). Requires the `gh` CLI authenticated.

```bash
# Sync everything (uses config.yaml defaults)
python github_project/sync_project.py

# Preview without writing
python github_project/sync_project.py --dry-run

# Sync only stories or only sprint tasks
python github_project/sync_project.py --sync stories
python github_project/sync_project.py --sync sprint

# Override config values
python github_project/sync_project.py --repo owner/repo --project 5 --owner owner

# Close all issues and remove from project
python github_project/sync_project.py --delete-all

# Preview deletion
python github_project/sync_project.py --delete-all --dry-run
```

---

## config.yaml

```yaml
project: Avaris AI
repo: owner/repo          # GitHub repo (owner/name)
owner: owner              # GitHub user or org
project: 4                # GitHub Projects v2 number
data_paths:
  sprint: github_project/issues/sprint.json
  stories: github_project/issues/stories.json
```

---

## Data structure

### stories.json

```json
{
  "stories": [
    {
      "id": "SK-001",
      "type": "Spike",
      "title": "Research feature X",
      "status": "In progress",
      "priority": "P0",
      "points": 3,
      "tdd": false,
      "blocked_by": [],
      "is_blocking": ["TS-002"],
      "acceptance_criteria": ["Criterion 1"]
    }
  ]
}
```

### sprint.json

```json
{
  "sprint": 1,
  "milestone": "v0.1.0",
  "tasks": [
    {
      "id": "T-001",
      "parent_story_id": "SK-001",
      "title": "Set up CI pipeline",
      "status": "Done",
      "priority": "P0",
      "complexity": "S",
      "blocked_by": [],
      "is_blocking": []
    }
  ]
}
```

#### Statuses: `Backlog` · `Ready` · `In progress` · `In review` · `Done`
#### Priorities: `P0` · `P1` · `P2` · `P3`
#### Complexity: `XS` · `S` · `M` · `L` · `XL`
