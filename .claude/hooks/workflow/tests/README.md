# Tests

Test suite for workflow hook components.

## Files

| File | Covers |
|------|--------|
| `test_workflow_architecture.py` | Config loading, phase engine, state manager, deliverables tracker |
| `test_phase_reminders.py` | Phase reminder loading and caching |
| `test_release_plan_tracker.py` | Release plan validation and recording |
| `test_criteria_validator.py` | AC/SC/epic SC validation detection |
| `test_revision_manager.py` | Revision task creation and tracking |
| `test_task_dod_stop.py` | Task DoD enforcement on Stop |
| `test_validation_integration.py` | End-to-end validation flow |

## Running Tests

All tests:
```bash
python -m pytest .claude/hooks/workflow/tests/ -v
```

Single file:
```bash
python -m pytest .claude/hooks/workflow/tests/test_criteria_validator.py -v
```

With coverage:
```bash
python -m pytest .claude/hooks/workflow/tests/ --cov=.claude/hooks/workflow -v
```
