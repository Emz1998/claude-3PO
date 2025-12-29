# Roadmap Utilities

Shared utilities for working with roadmap.json files in status loggers and workflow hooks.

## Overview

This module provides functions for:
- Loading and saving roadmap data
- Finding tasks, milestones, and phases
- Checking status and dependencies
- Auto-resolving milestone/phase completion
- Querying tasks by test strategy

## Installation

Import from the roadmap package:

```python
from roadmap import (
    load_roadmap,
    get_roadmap_path,
    find_task_in_roadmap,
)
```

## Type Aliases

| Type | Values |
|------|--------|
| `StatusType` | `"not_started"`, `"in_progress"`, `"completed"` |
| `CriteriaStatusType` | `"met"`, `"unmet"` |
| `TestStrategyType` | `"TDD"`, `"TA"` |

## Functions

### Path and Loading

| Function | Description |
|----------|-------------|
| `get_project_dir()` | Get project directory from env or cwd |
| `get_prd_path()` | Get path to PRD.json |
| `load_prd()` | Load PRD.json file |
| `get_current_version()` | Get current_version from PRD.json |
| `get_roadmap_path(version)` | Get roadmap.json path for version |
| `load_roadmap(path)` | Load roadmap.json file |
| `save_roadmap(path, roadmap)` | Save roadmap with updated timestamp |

### Find Utilities

| Function | Returns |
|----------|---------|
| `find_task_in_roadmap(roadmap, task_id)` | `(phase, milestone, task)` or `(None, None, None)` |
| `find_ac_in_roadmap(roadmap, ac_id)` | `(task, ac)` or `(None, None)` |
| `find_sc_in_roadmap(roadmap, sc_id)` | `(milestone, sc)` or `(None, None)` |
| `find_milestone_in_roadmap(roadmap, id)` | `(phase, milestone)` or `(None, None)` |
| `find_phase_in_roadmap(roadmap, id)` | `phase` or `None` |

### Phase Utilities

| Function | Description |
|----------|-------------|
| `is_checkpoint_phase(phase)` | Check if phase is a checkpoint |
| `get_checkpoint_phases(roadmap)` | Get all checkpoint phases |

### Milestone Utilities

| Function | Description |
|----------|-------------|
| `get_milestone_mcp_servers(milestone)` | Get MCP servers list |
| `has_mcp_servers(milestone)` | Check if milestone has MCP servers |

### Task Utilities

| Function | Description |
|----------|-------------|
| `get_task_test_strategy(task)` | Get test strategy (TDD/TA) |
| `is_tdd_task(task)` | Check if task uses TDD |
| `is_ta_task(task)` | Check if task uses TA |
| `get_task_owner(task)` | Get task owner/agent |
| `is_parallel_task(task)` | Check if task can run in parallel |

### Criteria Utilities

| Function | Description |
|----------|-------------|
| `get_ac_description(ac)` | Get acceptance criteria description |
| `get_sc_description(sc)` | Get success criteria description |
| `get_ac_with_description(task, ac_id)` | Find AC and return `(ac, description)` |
| `get_sc_with_description(milestone, sc_id)` | Find SC and return `(sc, description)` |

### Status Checking

| Function | Description |
|----------|-------------|
| `get_incomplete_task_deps(roadmap, task)` | Get incomplete dependency IDs |
| `get_incomplete_milestone_deps(roadmap, ms)` | Get incomplete milestone deps |
| `get_unmet_acs(task)` | Get unmet AC IDs |
| `get_unmet_scs(milestone)` | Get unmet SC IDs |
| `all_acs_met(task)` | Check if all ACs are met |
| `all_scs_met(milestone)` | Check if all SCs are met |
| `all_tasks_completed(milestone)` | Check if all tasks completed |
| `any_task_in_progress(milestone)` | Check if any task in progress |
| `all_milestones_completed(phase)` | Check if all milestones completed |
| `any_milestone_in_progress(phase)` | Check if any milestone in progress |

### Auto-Resolution

| Function | Description |
|----------|-------------|
| `resolve_milestones_and_phases(roadmap)` | Auto-resolve based on children status |
| `update_current_pointer(roadmap)` | Update current section to next pending |
| `update_summary(roadmap)` | Update summary counts |
| `run_auto_resolver()` | Run full auto-resolution pipeline |

### Query Utilities

| Function | Description |
|----------|-------------|
| `get_tdd_tasks(roadmap)` | Get all TDD tasks |
| `get_ta_tasks(roadmap)` | Get all TA tasks |
| `get_parallel_tasks(milestone)` | Get parallel tasks in milestone |
| `get_sequential_tasks(milestone)` | Get sequential tasks in milestone |
| `get_milestone_tasks(roadmap, milestone_id)` | Get all tasks from milestone by ID |

### Context Utilities

| Function | Description |
|----------|-------------|
| `get_task_context(task)` | Get summary context dict for task |
| `get_milestone_context(milestone)` | Get summary context dict for milestone |
| `get_phase_context(phase)` | Get summary context dict for phase |

### Current Pointer Utilities

| Function | Description |
|----------|-------------|
| `get_current_task()` | Get current task dict from roadmap |
| `get_current_milestone()` | Get current milestone dict from roadmap |
| `get_current_phase()` | Get current phase dict from roadmap |
| `get_current_task_id()` | Get current task ID |
| `get_current_milestone_id()` | Get current milestone ID |
| `get_current_phase_id()` | Get current phase ID |
| `get_current_task_test_strategy()` | Get current task's test strategy (TDD/TA) |

## Usage Examples

### Load and Find Task

```python
from roadmap import get_current_version, get_roadmap_path, load_roadmap, find_task_in_roadmap

version = get_current_version()
roadmap_path = get_roadmap_path(version)
roadmap = load_roadmap(roadmap_path)

phase, milestone, task = find_task_in_roadmap(roadmap, "T-001")
if task:
    print(f"Found task: {task['description']}")
```

### Check Dependencies

```python
from roadmap import find_task_in_roadmap, get_incomplete_task_deps

_, _, task = find_task_in_roadmap(roadmap, "T-002")
incomplete = get_incomplete_task_deps(roadmap, task)
if incomplete:
    print(f"Blocked by: {incomplete}")
```

### Run Auto-Resolver

```python
from roadmap import run_auto_resolver

success, messages = run_auto_resolver()
for msg in messages:
    print(msg)
```

## File Structure

```
roadmap/
├── __init__.py   # Package exports
├── roadmap.py    # Core utilities (load, find, status checks)
├── resolver.py   # Auto-resolver (status propagation, current pointer)
├── query.py      # CLI query tool
└── README.md     # This file
```
