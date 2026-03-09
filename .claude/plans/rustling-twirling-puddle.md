# Plan: Consolidate Workflow Hook Duplicates

## Context

After the recent subdirectory reorganization (18 root files → 7), there are still duplicate/versioned files that should be consolidated. This plan addresses the 3 highest-impact deduplication opportunities.

## Consolidation Items

### 1. Merge `file_manager.py` and `file_manager_v2.py` (HIGH)

**Files:** `lib/file_manager.py` (159 lines) + `lib/file_manager_v2.py` (195 lines)

**Difference:** v2 uses lazy lock creation (`create_file_lock()`) instead of eager `FileLock()` in `__init__`. v2 also adds `create_json_file()` and `create_jsonl_file()` methods. Free functions (`append_text`, `load_jsonl`, `load_file`, `write_file`, `update_file`, `set_default`) are identical.

**Current imports:**
- v2 used by: `state_store.py`, `context_injector.py`, `test/test.py`, `handlers/reminders.py`
- v1 used by: `sprint/sprint_config.py` (only consumer)

**Action:**
1. Delete `lib/file_manager.py`
2. Rename `lib/file_manager_v2.py` → `lib/file_manager.py`
3. Update import in `sprint/sprint_config.py`: `from workflow.lib.file_manager import FileManager` (no change needed — path stays the same after rename)
4. Update imports in 4 files using v2: change `file_manager_v2` → `file_manager`

**Files to modify:**
- `lib/file_manager.py` — DELETE
- `lib/file_manager_v2.py` — RENAME to `lib/file_manager.py`
- `state_store.py` line 7: `from workflow.lib.file_manager_v2` → `from workflow.lib.file_manager`
- `lib/context_injector.py` line 7: same change
- `test/test.py` line 19: same change
- `handlers/reminders.py` line 8: same change

### 2. Merge `hook_input.py` and `hook_input_v2.py` (HIGH)

**Files:** `models/hook_input.py` (89 lines) + `models/hook_input_v2.py` (117 lines)

**Difference:** v2 adds `EnterPlanModeTool` model, `ToolInputMap` dict for typed tool input instantiation via `@model_validator`, and changes `BaseToolUseInput` generics from `Generic[T]` to `Generic[T, U]`.

**Current imports:**
- v2 used by: `guards/pre_coding_phase.py`, `guards/code_phase.py`, `handlers/reminders.py`, `handlers/recorder.py`, `handlers/implement_trigger.py`, `initialize_state.py`
- v1 used by: `hook.py` (only consumer — imports `HookInput`, `PreToolUseInput`, `PostToolUseInput`, `UserPromptSubmitInput`, `StopInput`)

**Action:**
1. Delete `models/hook_input.py`
2. Rename `models/hook_input_v2.py` → `models/hook_input.py`
3. Update import in `hook.py` line 15: `from workflow.models.hook_input import ...` (no change needed — path stays the same after rename)
4. Update imports in 6 files using v2: change `hook_input_v2` → `hook_input`

**Files to modify:**
- `models/hook_input.py` — DELETE
- `models/hook_input_v2.py` — RENAME to `models/hook_input.py`
- `guards/pre_coding_phase.py` line 8: `from workflow.models.hook_input_v2` → `from workflow.models.hook_input`
- `guards/code_phase.py` line 8: same change
- `handlers/reminders.py` line 9: same change
- `handlers/recorder.py` line 8: same change
- `handlers/implement_trigger.py` line 8: same change
- `initialize_state.py` line 6: same change

### 3. Deduplicate `validate_order()` (MEDIUM)

**Files:** `utils/order_validation.py` (27 lines) + `guards/pre_coding_phase.py` (lines 16-41, identical copy)

**Current usage:**
- `guards/code_phase.py` imports from `workflow.utils.order_validation`
- `guards/pre_coding_phase.py` has its own inline copy

**Action:**
1. Remove `validate_order()` function from `guards/pre_coding_phase.py` (lines 16-41)
2. Add import: `from workflow.utils.order_validation import validate_order`

**Files to modify:**
- `guards/pre_coding_phase.py` — remove function, add import

---

## Execution Order

1. FileManager consolidation (step 1)
2. HookInput consolidation (step 2)
3. validate_order dedup (step 3)

## Verification

```bash
# Run existing tests
cd .claude/hooks/workflow && python -m pytest test/ -v

# Import checks
python -c "from workflow.lib.file_manager import FileManager; print('FileManager OK')"
python -c "from workflow.models.hook_input import PreToolUseInput, HookInput, EnterPlanModeTool; print('HookInput OK')"
python -c "from workflow.guards.pre_coding_phase import PreCodingPhaseGuard; print('PreCodingPhaseGuard OK')"

# Dry-run decision_handler (uses HookInput indirectly)
echo '{"tool_name":"Skill","tool_input":{"skill":"plan","args":""},"session_id":"x","transcript_path":"/tmp/x","cwd":"/tmp","permission_mode":"bypassPermissions","hook_event_name":"PreToolUse","tool_use_id":"t1"}' | python .claude/hooks/workflow/validation/decision_handler.py
```

## Critical Files

| File | Action |
|------|--------|
| `lib/file_manager.py` | DELETE (replaced by v2) |
| `lib/file_manager_v2.py` | RENAME → `lib/file_manager.py` |
| `models/hook_input.py` | DELETE (replaced by v2) |
| `models/hook_input_v2.py` | RENAME → `models/hook_input.py` |
| `state_store.py`, `lib/context_injector.py`, `test/test.py`, `handlers/reminders.py` | Update import path (file_manager_v2 → file_manager) |
| `guards/pre_coding_phase.py`, `guards/code_phase.py`, `handlers/recorder.py`, `handlers/implement_trigger.py`, `initialize_state.py` | Update import path (hook_input_v2 → hook_input) |
| `guards/pre_coding_phase.py` | Remove duplicate `validate_order()`, add import from utils |
