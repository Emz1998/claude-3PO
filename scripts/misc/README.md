# Scripts Directory

## Purpose

Automation scripts for Claude Code workflow and session management.

## Available Scripts

### Claude Launch Scripts

#### 1. launch-new-claude.sh

**Purpose**: Start a new Claude Code session

```bash
./scripts/launch-new-claude.sh
```

#### 2. launch-resume-claude.sh

**Purpose**: Resume an existing Claude Code session

```bash
./scripts/launch-resume-claude.sh
```

#### 3. launch-new-claude-yolo.sh

**Purpose**: Start Claude with auto-yes mode (skips permission prompts)

```bash
./scripts/launch-new-claude-yolo.sh
```

#### 4. launch-resume-claude-yolo.sh

**Purpose**: Resume Claude session with auto-yes mode

```bash
./scripts/launch-resume-claude-yolo.sh
```

### Multi-Session Scripts

#### 5. tmux-claude-sessions.py

**Purpose**: Spawn multiple tmux terminals for parallel Claude Code sessions

```bash
# Basic usage - spawn 2 Claude sessions as panes
python3 .claude/scripts/tmux-claude-sessions.py

# Spawn 3 sessions with tiled layout
python3 .claude/scripts/tmux-claude-sessions.py -n 3

# Spawn 4 sessions and attach immediately
python3 .claude/scripts/tmux-claude-sessions.py -n 4 --attach

# Use a specific pane layout
python3 .claude/scripts/tmux-claude-sessions.py -n 2 -l even-horizontal

# Use separate full-screen windows instead of panes
python3 .claude/scripts/tmux-claude-sessions.py -n 3 -w --attach
```

**Options**:

- `-n, --num-panes` - Number of panes/windows to spawn (default: 2)
- `-s, --session-name` - Tmux session name (default: claude-multi)
- `-l, --layout` - Pane layout: tiled, even-horizontal, even-vertical, main-horizontal, main-vertical
- `-w, --windows` - Use separate full-screen windows instead of panes
- `-p, --prefix` - Custom prefix key (e.g., `C-a`, `C-Space`). Default: `C-b`
- `-d, --working-dir` - Working directory for sessions
- `-c, --command` - Command to run in each pane (default: claude)
- `-a, --attach` - Attach to session after creating
- `-k, --kill` - Kill existing session
- `-f, --force` - Force recreate session
- `--no-run` - Create empty shells without running command
- `--list` - List all tmux sessions

**Navigation** (default prefix `Ctrl+b`, customizable with `-p`):

- Panes: Click with mouse or `PREFIX` then arrow keys
- Windows: `PREFIX` then `0-9` or `n`/`p` for next/previous
- Detach: `PREFIX` then `d`

**Requirements**: tmux must be installed (`sudo apt install tmux`)

### PRD Generator Scripts

#### 6. prd_to_markdown.py

**Purpose**: Generate PRD.md from product.json using templates

```bash
# Default: converts project/product/product.json to project/product/PRD.md
python3 .claude/scripts/prd_generator/prd_to_markdown.py

# Custom input/output paths
python3 .claude/scripts/prd_generator/prd_to_markdown.py -i path/to/product.json -o path/to/PRD.md

# Custom templates directory
python3 .claude/scripts/prd_generator/prd_to_markdown.py -t path/to/templates
```

**Options**:

- `-i, --input` - Input JSON file path (default: `project/product/product.json`)
- `-o, --output` - Output markdown file path (default: `project/product/PRD.md`)
- `-t, --templates` - Templates directory (default: `.claude/skills/product-management/templates`)

**Templates Used**:

- `PRD.md` - Main PRD document template
- `version.md` - Version section template
- `feature.md` - Feature section template
- `user_story.md` - User story template
- `risk.md` - Risk template

### Roadmap Scripts

#### 7. roadmap_status.py

**Purpose**: Update task, acceptance criteria (AC), or success criteria (SC) status in roadmap.json

```bash
# Task status updates
python3 .claude/scripts/roadmap_status/roadmap_status.py T001 in_progress
python3 .claude/scripts/roadmap_status/roadmap_status.py T002 completed
python3 .claude/scripts/roadmap_status/roadmap_status.py T003 blocked
python3 .claude/scripts/roadmap_status/roadmap_status.py T001 not_started

# Acceptance criteria status updates
python3 .claude/scripts/roadmap_status/roadmap_status.py AC-001 met
python3 .claude/scripts/roadmap_status/roadmap_status.py AC-002 unmet

# Success criteria status updates
python3 .claude/scripts/roadmap_status/roadmap_status.py SC-001 met
python3 .claude/scripts/roadmap_status/roadmap_status.py SC-002 unmet
```

**Positional Arguments**:

- `item_id` - Item ID in one of these formats:
  - Task: `TXXX` (e.g., T001, T002)
  - Acceptance Criteria: `AC-XXX` (e.g., AC-001, AC-002)
  - Success Criteria: `SC-XXX` (e.g., SC-001, SC-002)
- `status` - New status based on item type:
  - Task: `not_started`, `in_progress`, `completed`, `blocked`
  - AC/SC: `met`, `unmet`

**Features**:

- Auto-detects item type from ID format
- Validates status based on item type
- For tasks: checks dependencies before `in_progress`, checks ACs before `completed`
- Auto-resolves parent milestones and phases
- Updates current pointer and summary counts

#### 8. roadmap_query.py

**Purpose**: Query roadmap.json for project status, phases, milestones, tasks, AC, and SC

```bash
# Query types
python3 .claude/scripts/roadmap_status/roadmap_query.py todo         # Tasks with full context
python3 .claude/scripts/roadmap_status/roadmap_query.py version      # Project version info
python3 .claude/scripts/roadmap_status/roadmap_query.py current      # Current focus
python3 .claude/scripts/roadmap_status/roadmap_query.py phases       # List all phases
python3 .claude/scripts/roadmap_status/roadmap_query.py milestones   # List all milestones
python3 .claude/scripts/roadmap_status/roadmap_query.py tasks        # List all tasks
python3 .claude/scripts/roadmap_status/roadmap_query.py blockers     # Show blockers

# Filtered queries
python3 .claude/scripts/roadmap_status/roadmap_query.py milestones PH-001   # Milestones in phase
python3 .claude/scripts/roadmap_status/roadmap_query.py tasks MS-001        # Tasks in milestone
python3 .claude/scripts/roadmap_status/roadmap_query.py acs T001            # ACs for task
python3 .claude/scripts/roadmap_status/roadmap_query.py scs MS-001          # SCs for milestone

# Specific item queries
python3 .claude/scripts/roadmap_status/roadmap_query.py PH-001   # Phase details
python3 .claude/scripts/roadmap_status/roadmap_query.py MS-001   # Milestone details
python3 .claude/scripts/roadmap_status/roadmap_query.py T001     # Task details
python3 .claude/scripts/roadmap_status/roadmap_query.py AC-001   # AC details
python3 .claude/scripts/roadmap_status/roadmap_query.py SC-001   # SC details
```

**Query Types**:

- `todo` - Current tasks with full context (phase, milestone, feature, deps, ACs, SCs)
- `version` - Project version and summary
- `current` - Current phase/milestone/task focus
- `phases` - List all phases with completion status
- `milestones` - List all milestones (optional: filter by phase ID)
- `tasks` - List all tasks (optional: filter by milestone ID)
- `acs` - List acceptance criteria (optional: filter by task ID)
- `scs` - List success criteria (optional: filter by milestone ID)
- `blockers` - Blocked tasks and unmet criteria
- `metadata` - Roadmap metadata

**Specific ID Queries**:

- `PH-XXX` - Phase details (e.g., PH-001)
- `MS-XXX` - Milestone details (e.g., MS-001)
- `TXXX` - Task details (e.g., T001)
- `AC-XXX` - Acceptance criteria details (e.g., AC-001)
- `SC-XXX` - Success criteria details (e.g., SC-001)

#### 9. roadmap_to_markdown.py

**Purpose**: Convert project roadmap JSON to markdown format

```bash
# Default: converts schema.json to project/product/product.md
python3 .claude/scripts/roadmap_to_markdown.py

# Custom input/output paths
python3 .claude/scripts/roadmap_to_markdown.py -i path/to/roadmap.json -o path/to/output.md
```

**Options**:

- `-i, --input` - Input JSON file path (default: `.claude/skills/project-management/references/schema.json`)
- `-o, --output` - Output markdown file path (default: `project/product/product.md`)

### VS Code Setup Scripts

#### 10. init_tasks_json.py

**Purpose**: Initialize VS Code tasks.json with Claude Code launcher tasks

```bash
# Default: creates .vscode/tasks.json with 2 Claude launchers
python3 .claude/scripts/vscode_setup/init_tasks_json.py

# Create 3 Claude launcher tasks
python3 .claude/scripts/vscode_setup/init_tasks_json.py -n 3

# Preview without writing
python3 .claude/scripts/vscode_setup/init_tasks_json.py --dry-run

# Force overwrite existing file
python3 .claude/scripts/vscode_setup/init_tasks_json.py -f

# Disable auto-run on folder open
python3 .claude/scripts/vscode_setup/init_tasks_json.py --no-auto-run
```

**Options**:

- `-n, --num-tasks` - Number of Claude launcher tasks (default: 2)
- `-o, --output` - Output path (default: `.vscode/tasks.json`)
- `--no-auto-run` - Disable automatic run on folder open
- `-f, --force` - Overwrite without prompting
- `--dry-run` - Print content without writing
- `--milestones` - JSON array of milestones for worktree creation

#### 11. cleanup_worktrees.py

**Purpose**: Delete all git worktrees and their associated milestone branches

```bash
# Preview what would be deleted
python3 .claude/scripts/vscode_setup/cleanup_worktrees.py --dry-run

# Delete all milestone worktrees and branches
python3 .claude/scripts/vscode_setup/cleanup_worktrees.py

# Force delete even with uncommitted changes
python3 .claude/scripts/vscode_setup/cleanup_worktrees.py -f

# Only delete branches (keep worktree directories)
python3 .claude/scripts/vscode_setup/cleanup_worktrees.py --branches-only
```

**Options**:

- `-f, --force` - Force remove even with uncommitted changes
- `--dry-run` - Show what would be deleted without deleting
- `--branches-only` - Only delete branches, skip worktree removal

### Setup Scripts

#### 12. setup-yolo-aliases.sh

**Purpose**: Configure shell aliases for quick Claude commands

```bash
source ./scripts/setup-yolo-aliases.sh
```

Adds the following aliases:

- `yolo` - Run Claude with `--dangerously-skip-permissions`
- `yolo-r` - Resume Claude with auto-yes mode
- Additional worktree navigation shortcuts

## Integration with Development Container

These scripts are integrated with the development container through `.devcontainer/init-shortcuts.sh`, which automatically sets up:

- YOLO aliases for quick Claude operations
- Git worktree navigation functions
- Shell shortcuts for common tasks

## Prerequisites

- Bash shell
- Python 3 (for Python scripts)
- Claude CLI installed and configured
- Git (for worktree scripts)
- tmux (for multi-session scripts)

## Usage Notes

### YOLO Mode

The YOLO (You Only Launch Once) variants automatically accept all permission prompts, useful for:

- Automated workflows
- Experienced users who understand the risks
- Development environments where permissions are pre-approved

⚠️ **Warning**: YOLO mode skips safety prompts. Use with caution in production environments.

### Session Management

- New sessions start fresh with no prior context
- Resume sessions continue from the last saved state
- Sessions are automatically saved when Claude exits normally

## Troubleshooting

If scripts fail to execute:

1. Ensure execute permissions: `chmod +x scripts/*.sh`
2. Verify Claude CLI is installed: `which claude`
3. Check shell compatibility (scripts require Bash)

---

_Last updated: 2025-12-26_
