# Plan: Add install-deps, define-contracts phases + TaskCreated guardrail

## Context

The claudeguard workflow currently goes: explore -> research -> plan -> plan-review -> write-tests -> ... We need to:
1. Add two new phases after plan-review: `/install-deps` and `/define-contracts`
2. Auto-parse `## Dependencies`, `## Contracts`, and `## Tasks` sections from the plan on write
3. Add a `TaskCreated` hook that validates tasks match those extracted from the plan

## Phase ordering (new)

```
explore -> research -> plan -> plan-review -> install-deps -> define-contracts -> write-tests -> ...
```

---

## Step 1: State schema changes

### `scripts/models/state.py`
Add two new Pydantic models:

```python
class Dependencies(BaseModel):
    packages: list[str] = []      # package names from ## Dependencies
    installed: bool = False

class Contracts(BaseModel):
    file_path: str | None = None  # .claude/contracts/latest-contracts.md
    names: list[str] = []         # contract names extracted from contracts.md
    code_files: list[str] = []    # code files written during define-contracts
    written: bool = False         # contracts code files written
    validated: bool = False       # all contract names found in code files
```

Update `State` model:
- Add `dependencies: Dependencies = Dependencies()`
- Add `contracts: Contracts = Contracts()`
- Change `tasks: list[str] = []` — keep as `list[str]` (task subjects from ## Tasks)

### `scripts/utils/state_store.py`
Add properties and setters:
- `dependencies`, `set_dependencies_packages(packages)`, `set_dependencies_installed()`
- `contracts`, `set_contracts_file_path(path)`, `set_contracts_written()`
- `contract_names` — list of contract names extracted from plan (for resolver grep validation)
- `tasks` property already exists, `set_tasks(tasks: list[str])` — bulk setter for auto-parse

### `scripts/utils/initializer.py`
Update `build_initial_state()` to include:
```python
"dependencies": {"packages": [], "installed": False},
"contracts": {"file_path": None, "names": [], "written": False},
```

Add `archive_contracts(config)` — same pattern as `archive_plan()`:
- Live: `.claude/contracts/latest-contracts.md`
- Archive: `.claude/contracts/archive/contracts_{date}_{session_id}.md`
- Called during `initialize()` before state reset, alongside `archive_plan()`

---

## Step 2: Plan section parsing (auto-extract on write)

Both `latest-plan.md` and `latest-contracts.md` are written during the `/plan` phase.

### `scripts/utils/extractors.py`
Add extractors:

```python
def extract_plan_dependencies(content: str) -> list[str]:
    """Parse ## Dependencies section from plan — extract bullet items as package names."""

def extract_plan_tasks(content: str) -> list[str]:
    """Parse ## Tasks section from plan — extract bullet items as task subjects."""

def extract_contract_names(content: str) -> list[str]:
    """Parse contract names from latest-contracts.md — extract bullet/heading items."""
```

### `scripts/utils/recorder.py`
Add:
```python
def record_plan_sections(file_path: str, state: StateStore) -> None:
    """Auto-parse Dependencies and Tasks from plan and store in state."""

def record_contracts_file(file_path: str, state: StateStore) -> None:
    """Auto-parse contract names from contracts.md and store in state."""
```

### `scripts/post_tool_use.py`
- On plan Write: after `inject_plan_metadata()`, call `record_plan_sections()` to extract deps + tasks
- On contracts.md Write: call `record_contracts_file()` to extract contract names into `state.contracts.names`

### `scripts/utils/validators.py`
Update `is_file_write_allowed` — during `plan` phase, allow writes to BOTH:
- `config.plan_file_path` (`.claude/plans/latest-plan.md`)
- `config.contracts_file_path` (`.claude/contracts/latest-contracts.md`)

---

## Step 3: Config changes

### `scripts/config/config.toml`

```toml
MAIN_PHASES = ["explore", "research", "plan", "plan-review", "install-deps", "define-contracts", "write-tests", ...]
CODE_WRITE_PHASES = ["write-tests", "write-code", "install-deps", "define-contracts", "refactor"]
```

`install-deps` needs both Write (to package manager files like `package.json`, `requirements.txt`, `go.mod`) and Bash (install commands). Add to `CODE_WRITE_PHASES` for file writes, and COMMANDS_MAP for install commands.

Add to `[FILE_PATHS]`:
```toml
CONTRACTS_FILE_PATH = ".claude/contracts/latest-contracts.md"
CONTRACTS_ARCHIVE_DIR = ".claude/contracts/archive"
```

Add to `[REQUIRED_AGENTS]`:
```toml
install-deps = ""
define-contracts = ""
```

### `scripts/constants/constants.py`

Update `COMMANDS_MAP` — rename key `"install"` to `"install-deps"`:
```python
COMMANDS_MAP = {
    "install-deps": INSTALL_COMMANDS,
    ...
}
```

---

## Step 4: Validators for new phases

### `scripts/utils/validators.py`

**For plan content validation (enforce required sections)**:

_PreToolUse Write guard_ — in `is_file_write_allowed()`, when phase is `plan` and file is the plan path:
  - `tool_input` schema: `{ file_path: str, content: str }`
  - Read `tool_input["content"]` — this is the full file content being written
  - Check for required `## Dependencies`, `## Contracts`, `## Tasks` headers
  - Block Write if any are missing: `raise ValueError("Plan missing required sections: ...")`

_PreToolUse Edit guard_ — in `is_file_edit_allowed()`, when phase is `plan-review` and file is the plan path:
  - `tool_input` schema: `{ file_path: str, old_string: str, new_string: str, replace_all: bool }`
  - Read current file content from disk via `Path(file_path).read_text()`
  - Apply the patch: `patched = current_content.replace(old_string, new_string)` (or replace first occurrence only if `replace_all` is false)
  - Validate the patched content still has required `## Dependencies`, `## Contracts`, `## Tasks` headers
  - Block Edit if any section would be removed: `raise ValueError("Edit would remove required sections: ...")`

**For `install-deps`**:
- `is_command_allowed` already routes through `COMMANDS_MAP` — key `"install-deps"` restricts Bash to `INSTALL_COMMANDS`.
- Add path validation in `is_file_write_allowed()` — only allow package manager files:
  - `package.json`, `requirements.txt`, `Pipfile`, `go.mod`, `Cargo.toml`, `Gemfile`, `pyproject.toml`
  - Add `PACKAGE_MANAGER_FILES` list to `constants.py`

**For `define-contracts`**:
- Add path validation in `is_file_write_allowed()` — written code files must have valid code extensions
- Add `validate_contracts_in_code(state: StateStore) -> Result`:
  - Reads contract names from `state.contracts["names"]` (extracted from contracts.md)
  - Reads written code file paths from `state.contracts["code_files"]`
  - Greps each code file for each contract name
  - Raises `ValueError` with missing names if any are absent
  - Called from **phase guard** (PreToolUse for Skill) when transitioning OUT of define-contracts — blocks transition until all contracts are in code
  - On success, recorder sets `state.contracts["validated"] = True`

---

## Step 5: Recorders for new phases

### `scripts/utils/recorder.py`

**For `install-deps`**: 
- `record_dependency_install(command: str, state: StateStore)` — marks deps as installed when install command runs
- Called from `post_tool_use.py` when phase is `install-deps` and command matches INSTALL_COMMANDS

**For `define-contracts`**:
- Add to `record_file_write()`:
```python
elif phase == "define-contracts":
    state.set_contracts_written(True)
```

---

## Step 6: Resolvers for new phases

### `scripts/utils/resolvers.py`

```python
def resolve_install_dependencies(state: StateStore) -> None:
    """Complete when dependencies.installed is True."""
    deps = state.dependencies
    if deps.get("installed"):
        state.complete_phase("install-deps")

def resolve_define_contracts(state: StateStore) -> None:
    """Complete when contracts are validated and written as code."""
    contracts = state.contracts
    if contracts.get("written") and contracts.get("validated"):
        state.complete_phase("define-contracts")
```

Register both in the `resolvers` dict inside `resolve()`.

---

## Step 7: TaskCreated hook

### `scripts/task_created.py` (NEW)

New hook entrypoint following the same pattern as other hooks:

```python
#!/usr/bin/env python3
"""TaskCreated hook — validates task matches planned tasks."""

hook_input = Hook.read_stdin()
state = StateStore(...)
# Check workflow_active + session_id

task_subject = hook_input.get("task_subject", "")
planned_tasks = state.tasks  # list[str] from auto-parsed ## Tasks

# Normalize and match
normalized_subject = task_subject.strip().lower()
matched = any(
    normalized_subject == t.strip().lower() or
    t.strip().lower() in normalized_subject or
    normalized_subject in t.strip().lower()
    for t in planned_tasks
)

if not matched:
    Hook.block(f"Task '{task_subject}' does not match any planned task.\nPlanned tasks: {planned_tasks}")

# Also validate task_description is present and non-empty
task_description = hook_input.get("task_description", "")
if not task_description or not task_description.strip():
    Hook.block("Task must have a non-empty description.")

# else: exit 0 (allow)
```

### `hooks/hooks.json`

Add new entry:
```json
"TaskCreated": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/task_created.py",
        "timeout": 10
      }
    ]
  }
]
```

---

## Step 8: Slash commands

### `commands/install-deps.md` (NEW)

Phase instructions telling Claude to:
1. Read the plan's `## Dependencies` section
2. Write dependencies to the package manager file first (`package.json`, `requirements.txt`, `go.mod`, etc.)
3. Run the install command (`npm install`, `pip install -r requirements.txt`, etc.)
4. Verify installation

### `commands/define-contracts.md` (NEW)

Phase instructions telling Claude to:
1. Read `.claude/contracts/latest-contracts.md` (written during plan phase) for contract definitions
2. Write actual code files (interfaces, types, stubs) that implement those contracts
3. Validator greps written code files for all contract names from contracts.md
4. Phase completes when all contract names are found in code

### `commands/implement.md` (MODIFY)

Insert new phases between plan-review and write-tests:
- `### 5. /install-deps`
- `### 6. /define-contracts`
- Renumber subsequent phases (write-tests becomes 7, etc.)

---

## Step 9: PostToolUse updates

### `scripts/post_tool_use.py`

Add handling for:
1. **Plan write auto-parse**: After `inject_plan_metadata()`, call `record_plan_sections()` to extract deps/contracts/tasks from the plan
2. **Install command recording**: When phase is `install-deps` and Bash command matches install patterns, call `record_dependency_install()`

---

## Files summary

| File | Action | Purpose |
|------|--------|---------|
| `scripts/models/state.py` | Modify | Add Dependencies, Contracts models |
| `scripts/utils/state_store.py` | Modify | Add deps/contracts/tasks properties + setters |
| `scripts/utils/initializer.py` | Modify | Add deps/contracts to initial state |
| `scripts/utils/extractors.py` | Modify | Add plan section parsers |
| `scripts/utils/recorder.py` | Modify | Add plan section recording, dep install recording |
| `scripts/utils/resolvers.py` | Modify | Add resolve for both new phases |
| `scripts/utils/validators.py` | Modify | Add contracts path validation |
| `scripts/config/config.toml` | Modify | Add phases, agent config |
| `scripts/constants/constants.py` | Modify | Update COMMANDS_MAP key |
| `scripts/post_tool_use.py` | Modify | Add plan parse + dep install recording |
| `scripts/task_created.py` | Create | TaskCreated hook entrypoint |
| `hooks/hooks.json` | Modify | Add TaskCreated event |
| `commands/install-deps.md` | Create | Phase slash command |
| `commands/define-contracts.md` | Create | Phase slash command |
| `commands/implement.md` | Modify | Add new phases, renumber |

## Verification

1. **Unit tests**: Add tests in `scripts/tests/` for:
   - New extractors (plan section parsing)
   - New validators (contracts path validation)
   - New recorders (plan sections, dep install, contracts write)
   - New resolvers (install-deps, define-contracts)
   - TaskCreated hook (matching logic)
2. **Dry run**: Update `scripts/tests/dry_run.py` to exercise the full flow with new phases
3. **Integration**: Run `/implement` with a plan containing `## Dependencies`, `## Contracts`, `## Tasks` sections and verify phase flow
