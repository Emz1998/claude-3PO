# Complexity Assessment Report: `.claude/hooks/workflow/`

## Summary

- **HIGH:** 5
- **MEDIUM:** 8
- **LOW:** 4
- **Total:** 17

---

## HIGH Severity Findings

**1. Massive Code Duplication: `release_plan/state.py` is a God Module That Duplicates Everything**

- **Location:** `release_plan/state.py` (1101 lines)
- **Description:** This single file contains the complete implementation of getters, setters, checkers, resolvers, and initializers -- the exact same functions that are separately implemented in `release_plan/getters.py`, `release_plan/new_setters.py`, `release_plan/checkers.py`, and `release_plan/resolvers.py`. Every function exists in two places with identical logic.
- **Justification:** The `release_plan/__init__.py` imports from the separate modules, but `state.py` still contains its own complete implementations of all the same functions (e.g., `set_project_name`, `get_project_name`, `is_task_completed`, `record_completed_task`, `resolve_user_story`, etc.). Every change must be made in two places, and it is unclear which version is authoritative.

---

**2. Massive Code Duplication: Resolver Navigation Logic Copied 3x**

- **Location:** `release_plan/state.py:855-960`, `release_plan/resolvers.py:279-488`
- **Description:** The `resolve_user_story`, `resolve_feature`, and `resolve_epic` functions contain nearly identical 50+ line navigation blocks (find next US in feature, then find next feature in epic, then find next epic) that are duplicated between `state.py` and `resolvers.py`. Within each file, `resolve_feature` largely repeats `resolve_user_story`'s navigation logic, and `resolve_epic` repeats `resolve_feature`'s logic. The "initialize next items" block is copy-pasted at least 9 times across both files.
- **Justification:** This is the highest-cost duplication in the codebase. Any change to the navigation logic requires updating 6+ locations across 2 files, with high risk of inconsistency.

---

**3. Dual Legacy + New Architecture for State Management**

- **Location:** `state.py` (root), `core/state_manager.py`, `core/deliverables_tracker.py`
- **Description:** Two complete, parallel implementations of workflow state management exist:
  - **Legacy:** `state.py` at the root level with standalone functions (`load_state`, `save_state`, `get_state`, `set_state`, `mark_deliverable_complete`, etc.)
  - **New:** `core/state_manager.py` with `StateManager` class providing the exact same operations via methods, plus its own backward-compatible wrapper functions at the bottom of the file
- **Justification:** Three ways to do the same thing (legacy functions, class methods, convenience functions wrapping the class) with no clear deprecation path. `core/deliverables_tracker.py` wraps `StateManager` but adds almost no new logic -- it delegates 4 of 5 methods directly to the state manager.

---

**4. Dual Configuration Loaders**

- **Location:** `config/loader.py` (342 lines), `config/unified_loader.py` (726 lines)
- **Description:** Two complete configuration loading systems exist side-by-side:
  - `loader.py`: Loads YAML/JSON into raw dicts with `WorkflowConfig` dataclass
  - `unified_loader.py`: Loads YAML/JSON into a hierarchy of 8 dataclasses with validation, pattern conversion, and environment overrides
- **Justification:** The unified loader was clearly intended to replace the legacy loader, but both remain fully functional and both are imported by different modules. The config module exports 32 symbols from `__init__.py`.

---

**5. `release_plan/setters.py` and `release_plan/resolver.py` Are Dead/Legacy Modules**

- **Location:** `release_plan/setters.py` (194 lines), `release_plan/resolver.py` (139 lines)
- **Description:** `setters.py` operates on a completely different data model (roadmap phases/milestones/tasks with `flatten_dict` dependency) than the release plan state used everywhere else. It references `project/status.json` and `roadmap.json` rather than the `project/state.json` used by the actual release plan modules. Similarly, `resolver.py` imports from `roadmap.utils` and resolves a different data structure entirely.
- **Justification:** ~330 lines of code that appear completely orphaned from the current architecture. Neither module is imported by `release_plan/__init__.py`.

---

## MEDIUM Severity Findings

**6. Excessive Indirection: SubagentStopHandler -> DeliverablesExitGuard -> DeliverablesTracker -> StateManager**

- **Location:** `handlers/subagent_stop.py`, `guards/deliverables_exit.py`, `core/deliverables_tracker.py`, `core/state_manager.py`
- **Description:** To check deliverables on subagent stop: `SubagentStopHandler.run()` -> `DeliverablesExitGuard.run()` -> `DeliverablesTracker.are_all_met()` -> `StateManager.are_all_deliverables_met()`. That's 4 hops through 4 files to read a JSON file and check if all items have `completed: true`.
- **Justification:** 4-layer delegation chain where each layer adds minimal or no logic.

---

**7. Excessive Indirection: DeliverableTracker (tracker) -> DeliverablesTracker (core) -> StateManager**

- **Location:** `trackers/deliverables_tracker.py`, `core/deliverables_tracker.py`, `core/state_manager.py`
- **Description:** `trackers/deliverables_tracker.DeliverableTracker.track()` calls `core/deliverables_tracker.DeliverablesTracker.mark_complete()` which calls `StateManager.mark_deliverable_complete()`. The tracker class adds zero logic over the core class.
- **Justification:** 3-hop indirection with no added logic at the middle layer. Confusing near-identical naming (`DeliverableTracker` singular vs `DeliverablesTracker` plural).

---

**8. `phases.py` Constants Duplicated in `core/phase_engine.py`**

- **Location:** `phases.py:11-96`, `core/phase_engine.py:280-311`
- **Description:** The root-level `phases.py` defines `PHASES`, `TDD_PHASES`, `TA_PHASES`, `DEFAULT_PHASES`, `PHASE_SUBAGENTS`, `get_phase_order()`, and `get_all_phases()`. The `core/phase_engine.py` re-defines the exact same constants as "Legacy constants for backward compatibility" and re-implements the same functions wrapping the `PhaseEngine` class.
- **Justification:** Same constants and functions defined in two files. Either one is the source of truth, or neither is.

---

**9. Every Guard/Tracker/Handler Has Triple Entry Points**

- **Location:** All files in `guards/`, `trackers/`, `handlers/`
- **Description:** Every module follows the pattern of: (1) a class with a `run()` method, (2) a standalone function that creates an instance and calls the method, (3) a `main()` function + `__main__` block that reads stdin and calls the class.
- **Justification:** The classes have a single caller each (the handler router). The standalone functions are exported via `__init__.py` but it's unclear if they're used. The `main()` functions are only needed if the file is run directly as a hook script, but the current architecture routes through handlers instead.

---

**10. `release_plan/__init__.py` Exports 60+ Symbols**

- **Location:** `release_plan/__init__.py` (189 lines)
- **Description:** The `__init__.py` file imports and re-exports 60+ functions organized across 4 categories (getters, setters, checkers, resolvers). This creates a massive public API surface for what is an internal module.
- **Justification:** A 189-line `__init__.py` that is purely import/export statements suggests the module boundary is too broad.

---

**11. Repeated State Load/Save Pattern in Release Plan**

- **Location:** All `release_plan/` modules (`new_setters.py`, `resolvers.py`, `checkers.py`, `getters.py`)
- **Description:** Every single function follows the pattern: `def some_function(param, state=None): if state is None: state = _load_state()` ... do one thing ... `_save_state(state)`. Each setter calls `_load_state()` and `_save_state()` independently, meaning `resolve_user_story()` does 15+ separate load/save cycles to the same JSON file.
- **Justification:** Extreme I/O overhead. The `resolve_user_story` function in `resolvers.py` calls `_load_state()` approximately 12 times in a single execution path.

---

**12. Unused Features: Environment Overrides**

- **Location:** `config/unified_loader.py:119`, `config/unified_loader.py:552-556`
- **Description:** `UnifiedWorkflowConfig` has an `environments` field and `load_unified_config` accepts an `environment` parameter for environment-based configuration overrides. No caller passes an environment value. The config files don't define any environments.
- **Justification:** Premature generalization for a feature that has no usage.

---

**13. `config/workflow_config.json` and `config/workflow.config.yaml` Both Exist**

- **Location:** `config/workflow_config.json` (4,539 bytes), `config/workflow.config.yaml` (8,601 bytes)
- **Description:** Both configuration files exist and both loaders try them in order (YAML first, JSON fallback with deprecation warning). Since the YAML file exists and takes precedence, the JSON file can never be loaded.
- **Justification:** The JSON file exists purely as a migration artifact and is dead code.

---

## LOW Severity Findings

**14. `deliverables/` Module Contains Only `__init__.py`**

- **Location:** `deliverables/__init__.py`
- **Description:** The `deliverables/` directory contains a single `__init__.py` file. The actual deliverables tracking logic lives in `core/deliverables_tracker.py` and `trackers/deliverables_tracker.py`.
- **Justification:** Empty module that serves no purpose.

---

**15. `phase_reminders.py` Exists at Both Root and `context/` Level**

- **Location:** `phase_reminders.py` (root, 178 lines), `context/phase_reminders.py`
- **Description:** Phase reminder logic appears at two levels in the directory hierarchy.
- **Justification:** Minor duplication of concern across directory levels.

---

**16. Test Function Left in Production Code**

- **Location:** `release_plan/state.py:127-160` (`test_project_state()`)
- **Description:** A `test_project_state()` function exists in the production `state.py` file. It's essentially a copy of `initialize_project_state()` with additional fields, and calls `set_all_status_in_progress` and `set_all_status_completed` sequentially.
- **Justification:** Test code in production module.

---

**17. `WORKFLOW_CONFIG_GUIDE.md` (9,791 bytes) in Config Directory**

- **Location:** `config/WORKFLOW_CONFIG_GUIDE.md`
- **Description:** A nearly 10KB guide document lives inside the config source directory alongside the code. This documentation is better suited to the `docs/` directory or the README.
- **Justification:** Cosmetic organizational issue.

---

## Architectural Observations (Non-Findings)

_These are structural observations that don't qualify as overengineering but provide context:_

1. The `release_plan/` module is the most complex subsystem (~1800+ lines across 8 files) and contains the most severe duplication issues. It manages a hierarchical state machine (epic -> feature -> user story -> task -> AC/SC) with navigation logic that is inherently complex, but the duplication amplifies the maintenance burden significantly.
2. The "backward compatibility" layer accounts for ~30% of total code. Almost every module maintains both a class-based API and standalone function wrappers "for backward compatibility." It's unclear which consumers depend on the legacy API.
3. The `sys.path.insert(0, ...)` pattern appears in every single file (30+ occurrences), often twice per file, to enable cross-module imports. This is a consequence of the flat hook script architecture where each file may be invoked independently.
