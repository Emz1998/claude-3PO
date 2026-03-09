# Plan: Revise Scripts to Use project_manager.py

## Context

The project has migrated from a hierarchical `roadmap.json` (phases -> milestones -> tasks) to a flat model using `github_project/issues/sprint.json` + `stories.json`, managed by `github_project/project_manager.py`. Several scripts in `.claude/scripts/` still reference the old roadmap system and need to be cleaned up.

## Changes

### 1. Delete obsolete scripts

These scripts are fully superseded by `project_manager.py`:

| Delete | Reason |
|--------|--------|
| `.claude/scripts/roadmap_status/roadmap_status.py` | Status updates -> `project_manager.py update T-001 --status "In progress"` |
| `.claude/scripts/roadmap_status/README.md` | Documentation for deleted script |
| `.claude/scripts/roadmap_filler/roadmap_generator.py` | Phase/milestone template generation - no equivalent in flat model |
| `.claude/scripts/roadmap_filler/status.py` | Old `project/status.json` reader - sprint info now in sprint.json |
| `.claude/scripts/roadmap_filler/templates/phase.md` | Template for deleted generator |

Delete entire directories: `roadmap_status/`, `roadmap_filler/`

### 2. Revise `init_tasks_json.py`

**File**: `.claude/scripts/vscode_setup/init_tasks_json.py`

Changes:
- Rename `--milestones` arg to `--stories`
- Add `--from-stories` flag that auto-reads from `github_project/issues/stories.json` via importing `_load_stories` from `project_manager.py`
- Update `create_worktree()` branch naming from `milestones/{id}_{name}` to `feat/{story_id}` (matching `launch-claudes.py` convention)
- Update label format to `"Launch Claude - {story_id}"`

### 3. No changes needed

- `launch-claudes.py` - Already uses correct story ID patterns (US/TS/SK/BG-XXX)
- `cleanup_worktrees.py` - Generic worktree cleanup, works with any branch naming

### 4. Update README.md

**File**: `.claude/scripts/README.md`

- Remove sections 7-9 (roadmap_status.py, roadmap_query.py, roadmap_to_markdown.py)
- Add section for `project_manager.py` with usage examples
- Update `init_tasks_json.py` docs to reflect `--stories` / `--from-stories`

## Critical Files

- `/home/emhar/avaris-ai/github_project/project_manager.py` - Import `_load_stories` in init_tasks_json.py
- `/home/emhar/avaris-ai/.claude/scripts/vscode_setup/init_tasks_json.py` - Revise
- `/home/emhar/avaris-ai/.claude/scripts/launch-claudes.py` - Reference for `feat/{story_id}` branch naming (line 33)
- `/home/emhar/avaris-ai/.claude/scripts/README.md` - Update docs

## Verification

1. Run `python github_project/project_manager.py list` to confirm project_manager.py works
2. Run `python .claude/scripts/vscode_setup/init_tasks_json.py --from-stories --dry-run` to verify story-based worktree creation
3. Confirm deleted directories no longer exist
4. Verify no remaining imports/references to deleted scripts via grep
