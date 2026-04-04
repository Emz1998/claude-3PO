# Plan: Async Auto-Commit Hook on TaskCompleted

## Context

Create an async hook that fires after each `TaskCompleted` event. It detects dirty files via `git status`, batches them into a state file, invokes headless Claude (`claude -p`) to generate a commit message, then commits the files — all without blocking the main session.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `.claude/hooks/workflow/auto_commit.py` | **Create** | Main async hook script |
| `.claude/hooks/workflow/config/paths.py` | **Modify** | Add `COMMIT_BATCH_PATH` constant |
| `.claude/hooks/workflow/config/__init__.py` | **Modify** | Export new constant |
| `.claude/settings.local.json` | **Modify** | Register async hook alongside existing sync hook |

## Implementation (TDD)

All steps follow TDD: write failing tests first, then implement to make them pass.

### Step 0: Commit message format guard (TDD)

#### Step 0a: Write tests first

**`.claude/hooks/workflow/tests/test_bash_guard.py`** — Add a new test class `TestCommitFormatValidation`:

```python
class TestCommitFormatValidation:
    # Valid conventional commits → allowed
    def test_valid_feat_commit(self, tmp_state_file): ...
    def test_valid_fix_with_scope(self, tmp_state_file): ...
    def test_valid_chore_commit(self, tmp_state_file): ...
    def test_valid_breaking_change(self, tmp_state_file): ...
    def test_valid_refactor_docs_test_style_perf_ci_build_revert(self, tmp_state_file): ...

    # Invalid commits → blocked
    def test_missing_type_prefix(self, tmp_state_file): ...
    def test_missing_colon_space(self, tmp_state_file): ...
    def test_invalid_type(self, tmp_state_file): ...
    def test_empty_description(self, tmp_state_file): ...

    # Non-commit commands → allowed (pass-through)
    def test_non_commit_command_allowed(self, tmp_state_file): ...
    def test_git_commit_without_m_flag_allowed(self, tmp_state_file): ...

    # Workflow inactive → allowed regardless
    def test_commit_allowed_when_workflow_inactive(self, tmp_state_file): ...

    # Multiline commit messages (heredoc) → validate first line only
    def test_multiline_commit_first_line_valid(self, tmp_state_file): ...
```

#### Step 0b: Implement to pass tests

**`.claude/hooks/workflow/guards/bash_guard.py`** — Add a `validate_commit_format()` function that runs when `workflow_active` is true (workflow-scoped, like all other guards).

This is called from within the existing `validate_pre()` flow — when the command is a `git commit`, validate the message format before allowing it.

**Logic:**
1. Check if command matches `git commit` (with `-m` flag)
2. Extract the commit message from the command
3. Validate it matches conventional commit format: `type(scope): description` or `type: description`
4. Valid types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `style`, `perf`, `ci`, `build`, `revert`
5. If invalid → block with reason explaining the expected format
6. If valid or not a git commit → allow

**Regex pattern:**
```python
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|chore|refactor|docs|test|style|perf|ci|build|revert)"
    r"(\(.+\))?"   # optional scope
    r"!?"           # optional breaking change indicator
    r": .+"         # colon + space + description
)
```

**Changes to `bash_guard.validate_pre()`** — Add commit format check inside the existing function (after the `workflow_active` check, before the PR command check):
```python
def validate_pre(hook_input: dict, store: StateStore) -> tuple[str, str]:
    state = store.load()
    if not state.get("workflow_active"):
        return "allow", ""

    command = hook_input.get("tool_input", {}).get("command", "")

    # Commit message format enforcement
    result = validate_commit_format(command)
    if result[0] == "block":
        return result

    # ... existing PR command checks ...
```
No changes to `guardrail.py` needed — it already calls `bash_guard.validate_pre()`.

### Step 1: Add path constant

**`.claude/hooks/workflow/config/paths.py`** — Add:
```python
COMMIT_BATCH_PATH = WORKFLOW_ROOT / "commit_batch.json"
```

**`.claude/hooks/workflow/config/__init__.py`** — Add `COMMIT_BATCH_PATH` to the imports from `workflow.config.paths`.

### Step 2: Create `auto_commit.py` (TDD)

#### Step 2a: Write tests first

**`.claude/hooks/workflow/tests/test_auto_commit.py`** — New test file:

```python
class TestGetDirtyFiles:
    def test_returns_modified_files(self): ...
    def test_excludes_state_json(self): ...
    def test_excludes_pyc_files(self): ...
    def test_excludes_pycache_dirs(self): ...
    def test_returns_empty_when_clean(self): ...

class TestClaimFiles:
    def test_claims_all_files_when_no_pending_batches(self): ...
    def test_excludes_files_from_pending_batches(self): ...
    def test_returns_empty_when_all_files_claimed(self): ...
    def test_reclaims_stale_pending_batches(self): ...

class TestGenerateCommitMessage:
    def test_returns_claude_output(self): ...  # mock subprocess
    def test_fallback_on_claude_failure(self): ...
    def test_fallback_on_timeout(self): ...

class TestCommitFiles:
    def test_stages_and_commits(self): ...  # real git repo in tmp_path
    def test_handles_commit_failure(self): ...

class TestBatchLedger:
    def test_saves_batch_with_pending_status(self): ...
    def test_updates_batch_to_committed(self): ...
    def test_cleans_up_old_committed_batches(self): ...

class TestEndToEnd:
    def test_full_flow_with_dirty_files(self): ...  # mock claude, real git
    def test_skip_when_no_dirty_files(self): ...
    def test_concurrent_batches_dont_overlap(self): ...
```

#### Step 2b: Implement to pass tests

**`.claude/hooks/workflow/auto_commit.py`** — New file, executable (`chmod +x`).

#### Batch Ledger Design (Prevents Cross-Batch Contamination)

**Problem:** If batch 1 hasn't committed yet when batch 2 fires, batch 2's `git status` would include batch 1's files — causing duplicate commits or conflicts.

**Solution:** Use `commit_batch.json` as a ledger that tracks file ownership per batch. Files claimed by a pending batch are excluded from subsequent batches.

**Batch state structure:**
```json
{
  "batches": [
    {
      "batch_id": "batch-1712345678-abc1",
      "task_id": "task-001",
      "task_subject": "Implement auth",
      "files": ["src/auth.py", "src/utils.py"],
      "status": "pending",
      "created_at": "2026-04-04T10:00:00"
    },
    {
      "batch_id": "batch-1712345679-def2",
      "task_id": "task-002",
      "task_subject": "Add tests",
      "files": ["tests/test_auth.py"],
      "status": "committed",
      "commit_message": "test: add auth tests",
      "created_at": "2026-04-04T10:00:05"
    }
  ]
}
```

#### Flow (Two-Phase Locking)

The lock is held during the fast "claim files" phase, released during the slow headless Claude call, then re-acquired for the commit phase:

**Phase 1 — Claim files (lock held):**
1. Read stdin JSON (gets `task_subject`, `task_id`, etc.)
2. Acquire file lock on `commit_batch.json`
3. Load existing batches from ledger
4. Collect all files from batches with `status: "pending"` → **already claimed set**
5. Run `git status --porcelain` → get all dirty files
6. Filter out excluded patterns (state.json, *.pyc, __pycache__, lock files, logs, settings.local.json)
7. Subtract already-claimed files → **this batch's files**
8. If no remaining files → log skip, release lock, exit
9. Write new batch entry with `status: "pending"` to ledger
10. Release lock

**Phase 2 — Generate message (no lock):**
11. Run headless Claude to generate commit message

**Phase 3 — Commit (lock held):**
12. Re-acquire file lock
13. `git add <files>` (only this batch's files)
14. `git commit -m "<message>"`
15. Update batch entry status to `"committed"` in ledger
16. Clean up old committed batches (keep last 10)
17. Release lock
18. Log success, output `systemMessage`

#### Headless Claude Command

Do NOT use `--bare`. Use `--tools` to restrict to read-only tools and `--allowedTools` to auto-approve them:

```python
result = subprocess.run(
    [
        "claude", "-p", prompt,
        "--tools", "Read,Grep,Glob",
        "--allowedTools", "Read,Grep,Glob",
        "--output-format", "text",
    ],
    capture_output=True, text=True, timeout=120,
    cwd=project_dir,
)
```

- `--tools "Read,Grep,Glob"` — restricts to read-only tools (no Bash, Edit, Write)
- `--allowedTools "Read,Grep,Glob"` — auto-approves those tools without prompts
- No `--bare` — headless Claude loads full context (CLAUDE.md, hooks, skills, MCP)
- `--output-format text` — plain text output for easy parsing

The prompt should ask Claude to generate a conventional commit message:
```
Generate a concise git commit message for the following changes.
Task: {task_subject}
Description: {task_description}
Files changed:
{file_list}
Use conventional commit format (feat/fix/chore/refactor/docs/test).
Keep the first line under 72 characters. Add a body if the changes warrant it.
Respond with ONLY the commit message text, nothing else.
```

Both `task_subject` and `task_description` come from the TaskCompleted hook input JSON.

#### Key Design Decisions
- **Two-phase locking** — lock held only during fast claim/commit steps, released during slow headless Claude call. This means multiple batches can generate commit messages concurrently without blocking each other.
- **File ownership via ledger** — pending batch files are excluded from subsequent batches, preventing duplicate commits.
- **`StateStore`/`FileManager`** on `commit_batch.json` provides file locking (`.lock` sibling)
- **Fallback commit message** if headless Claude fails: `"chore: auto-commit after task ({task_subject})"`
- **Batch cleanup** — keep only last 10 committed batches to prevent unbounded growth
- **Exclude patterns**: `state.json`, `*.pyc`, `__pycache__/`, `commit_batch.json`, `workflow.log`, `locks/`, `settings.local.json`

### Step 3: Register async hook in settings

**`.claude/settings.local.json`** — Add second entry to `TaskCompleted` array:

```json
"TaskCompleted": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/dispatchers/task_completed.py",
        "timeout": 30
      }
    ]
  },
  {
    "hooks": [
      {
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/workflow/auto_commit.py",
        "timeout": 120,
        "async": true
      }
    ]
  }
]
```

- `timeout: 120` — headless Claude can take 30-60s, plus git ops
- `async: true` — non-blocking, output delivered next turn

## Execution Flow

```
TaskCompleted #1 fires                    TaskCompleted #2 fires (shortly after)
  |                                         |
  +---> [async] auto_commit.py              +---> [async] auto_commit.py
          |                                         |
  [LOCK]  +-- Load ledger                           |  (waiting for lock)
          +-- pending files = {}                     |
          +-- git status → [A, B, C]                 |
          +-- this batch = [A, B, C]                 |
          +-- Save batch#1 (pending)                 |
  [UNLOCK]+-- Release lock                           |
          |                                  [LOCK]  +-- Load ledger
          +-- claude -p "commit msg"                 +-- pending files = {A, B, C}  ← from batch#1
          |   (slow, ~30-60s)                        +-- git status → [A, B, C, D, E]
          |                                          +-- this batch = [D, E]  ← only new files!
          |                                          +-- Save batch#2 (pending)
          |                                  [UNLOCK]+-- Release lock
  [LOCK]  +-- git add A B C                          |
          +-- git commit                             +-- claude -p "commit msg"
          +-- batch#1 → "committed"                  |
  [UNLOCK]                                   [LOCK]  +-- git add D E
                                                     +-- git commit
                                                     +-- batch#2 → "committed"
                                             [UNLOCK]
```

## Edge Cases

1. **No dirty files** → skip, log, exit
2. **No unclaimed files** (all dirty files belong to pending batches) → skip, log, exit
3. **Headless Claude fails** → fallback to template message `chore: auto-commit after task (subject)`
4. **Concurrent firings** → two-phase locking ensures each batch claims unique files
5. **Git commit fails** → catch CalledProcessError, mark batch as `"failed"` in ledger, log, exit
6. **Stale pending batch** (process died mid-flight) → clean up batches older than 10 minutes with `status: "pending"` during the claim phase, releasing their files back to the pool
7. **Recursive prevention** → headless Claude only has read-only tools, cannot trigger write-based hooks

## Verification

1. Make a file change, trigger TaskCompleted manually:
   ```bash
   echo '{"hook_event_name":"TaskCompleted","task_id":"test-1","task_subject":"Test task","session_id":"test","cwd":"/home/emhar/avaris-ai"}' | python3 .claude/hooks/workflow/auto_commit.py
   ```
2. Check `git log -1` to verify commit was created with a sensible message
3. Check `commit_batch.json` shows batch with status "committed"
4. Check `workflow.log` for AutoCommit log entries
5. Test concurrent batches: make changes, fire two TaskCompleted events rapidly, verify two separate commits with non-overlapping file sets
6. Test stale batch cleanup: create a pending batch with old timestamp, fire new TaskCompleted, verify stale files are reclaimed
