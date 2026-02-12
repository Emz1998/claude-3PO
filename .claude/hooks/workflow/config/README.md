# Config

Centralized configuration management for the workflow system.

## Files

| File                       | Purpose                                                            |
| -------------------------- | ------------------------------------------------------------------ |
| `unified_loader.py`        | YAML config loader with caching, validation, and typed dataclasses |
| `workflow.config.yaml`     | Main configuration: phases, agents, deliverables, project settings |
| `WORKFLOW_CONFIG_GUIDE.md` | User guide for editing configuration                               |
| `reminders/`               | Phase-specific reminder markdown files                             |

## Key Exports

- `UnifiedWorkflowConfig` - Complete typed configuration dataclass
- `load_unified_config()` - Load and cache configuration from YAML
- `get_agent_for_phase()` - Look up agent assigned to a phase
- `get_phase_deliverables_typed()` - Get typed deliverables for a phase
- `get_project_settings()` / `get_feature_flags()` - Access specific config sections
- `wildcard_to_regex()` / `regex_to_wildcard()` - Pattern conversion utilities
- `resolve_filepath_placeholders()` - Resolve `{project}` and `{session}` placeholders in filepaths
- `validate_config()` - Validate raw config dict and return issues

## Configuration Structure

```yaml
project:
  name: "..."
  version: "v0.1.0"

phases:
  base: [explore, plan, code, commit]
  tdd: [write-test, review-test, write-code, code-review, refactor]
  test-after: [write-code, write-test, code-review, refactor]

agents:
  explore: codebase-explorer
  plan: planning-specialist
  # ...

deliverables:
  explore:
    read:
      - filepath: "./prompt.md"        # Exact match at repo root
      - filepath: "{project}/docs/*.md" # With placeholder
  # ...
```

## Caching

Configuration is cached at module level after first load. Call `clear_unified_cache()` to force reload.
