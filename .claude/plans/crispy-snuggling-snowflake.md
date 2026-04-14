# Plan: Fix stop hook test_mode bypass (BUG-002)

## Context

Third E2E test run found 2 bugs. BUG-001 (`/revise-plan` args parsing) is a Claude Code platform behavior — `$1` substitution is handled by the runtime, not our code. BUG-002 is fixable.

**BUG-002 (High)**: Stop hook doesn't block before write-report because `test_mode` bypass exits 0 immediately, skipping ALL checks including `check_phases`. The stop hook should still verify phase completion in test mode — only `check_tests` and `check_ci` need skipping (those require real test execution and CI runs that don't happen in E2E tests).

## Fix

**File:** `claudeguard/scripts/stop.py`

Replace the blanket test_mode bypass with a selective one. In test_mode, run `check_phases` but skip `check_tests` and `check_ci`:

```python
# Current (broken):
if state.get("test_mode"):
    sys.exit(0)

# Fixed:
checks = [
    lambda: check_phases(config, state),
]
if not state.get("test_mode"):
    checks += [
        lambda: check_tests(state),
        lambda: check_ci(state),
    ]
```

This means `config = Config()` must move above the test_mode check.

## Files to Modify

| Action | Path |
|--------|------|
| Modify | `claudeguard/scripts/stop.py` |

## Verification

- `python -m pytest claudeguard/scripts/tests/ -p no:randomly` — all tests pass
- `python claudeguard/scripts/tests/dry_run.py` — build dry run passes
