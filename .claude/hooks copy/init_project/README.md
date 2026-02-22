# Init Project Hooks

Hooks for project initialization and setup.

## Files

**init_status.py** - Initialize project status.json
- Uses Pydantic models for validation
- Creates status.json with default structure

**init_dir.py** - Create project directory structure
- Sets up required folders
- Initializes project scaffolding

**project_schema.py** - Schema definitions
- Pydantic models for project data

## Status Schema

```python
class Status(BaseModel):
    project: Project      # name, version, target_release, status
    specs: Specs          # prd, tech, ux status and paths
    summary: Summary      # phases, milestones, tasks counts
    current: Current      # phase, milestone, task
    phases: dict          # phase details
    metadata: Metadata    # last_updated, schema_version
```

## Usage

```python
from init_project.init_status import init_and_save_status

init_and_save_status(
    project_name="My Project",
    version="0.1.0",
    target_release="2026-01-01"
)
```

## Output

Creates `project/status.json` with:
- Project metadata
- Spec tracking (PRD, Tech, UX)
- Summary counters
- Current progress pointers
- Phase structure
