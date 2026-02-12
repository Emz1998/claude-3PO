# Core

Foundational building blocks for workflow orchestration: state management, phase ordering, and deliverables tracking.

## Files

| File | Purpose |
|------|---------|
| `state_manager.py` | Unified API for workflow state operations (`state.json`) |
| `phase_engine.py` | Phase definitions, ordering, transitions, and subagent mappings |
| `deliverables_tracker.py` | Deliverable initialization and completion tracking |
| `workflow_auditor.py` | Invariant checks and violation logging for post-hoc audit |

## Key Classes

### StateManager
Singleton class managing `state.json`. Provides:
- `is_workflow_active()` / `set_workflow_active()`
- `get_current_phase()` / `set_current_phase()`
- `get_deliverables()` / `set_deliverables()` / `mark_deliverable_complete()`
- `get_pending_validation()` / `set_pending_validation()`

### PhaseEngine
Singleton class managing phase ordering. Provides:
- `phases` - Ordered list of phases based on test strategy (tdd/test-after/none)
- `is_valid_transition(current, next)` - Validate phase progression
- `get_subagent(phase)` - Look up agent for a phase
- `get_next_phase()` / `get_previous_phase()`

### DeliverablesTracker
Manages deliverable lifecycle per phase. Provides:
- `initialize_for_phase(phase)` - Load deliverables from config
- `mark_complete(pattern)` - Mark a deliverable as done
- `are_all_met()` - Check if all required deliverables are complete

### WorkflowAuditor
Detects guard failures and state corruption. Never breaks workflow - all errors are silently caught. Provides:
- `check_strict_order_compliance(deliverables)` - Verify strict_order invariant
- `check_phase_validity(phase)` - Verify phase exists in config
- `check_empty_deliverables(phase, deliverables)` - Warn on zero deliverables
- `check_state_integrity(state)` - Verify required keys exist with correct types
- `check_state_corruption(state, was_fallback)` - Detect JSON corruption
- `check_phase_deliverable_match(phase, deliverables)` - Verify count matches config
- `log_decision(guard, outcome, context)` - Log guard decisions for audit trail
- `log_warn(check, message)` - Log non-invariant warnings

Logs written to `logs/violations.log` with automatic rotation at 5MB.

## Singleton Access

```python
from core.state_manager import get_manager
from core.phase_engine import get_engine
from core.workflow_auditor import get_auditor
```
