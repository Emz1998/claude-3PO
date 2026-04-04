---
name: claude-scripts
description: Creates and updates automation scripts in .claude/scripts/ directory. Use when user mentions creating scripts, automation tools, workflow utilities, or needs to manage scripts for Claude Code sessions.
---

**Goal**: Create or update automation scripts in `.claude/scripts/` for Claude Code workflows

## Workflow

1. Read `.claude/scripts/README.md` to understand existing scripts and patterns
2. Explore relevant subdirectories if the script belongs to a category
3. Create a subdirectory for the script if it doesn't exist inside `.claude/scripts/` directory.
4. Create or update the script following project conventions
5. Update `.claude/scripts/README.md` if adding a new script
6. Test the script execution

## Script Categories

| Category          | Purpose                    |
| ----------------- | -------------------------- |
| Root (`scripts/`) | General automation scripts |
| `utils/`          | Shared Python utilities    |
| `ai_discussion/`  | AI discussion tools        |
| `hooks_toggler/`  | Hook activation scripts    |
| `phase_creator/`  | Phase management tools     |
| `roadmap_filler/` | Roadmap automation         |

## Rules

- **MUST** prefer Python over shell scripts
- **MUST** use type hints for Python scripts
- **MUST** include proper error handling
- **MUST** use `#!/usr/bin/env python3` shebang for Python scripts
- **MUST** use `argparse` for command-line arguments
- **MUST** import shared utilities from `.claude/scripts/utils/` when available
- **DO NOT** hardcode paths - use `Path(__file__).parent` for relative paths
- **DO NOT** include credentials or secrets in scripts
- **MUST** use `Path(__file__).parent` for relative paths
- **MUST** use `# type: ignore` to suppress type errors
- **MUST** use single line comments `#` and avoid multi-line comments `'''` or `"""`, unless necessary for documentation.

## Python Script Template

```python
#!/usr/bin/env python3
"""Brief description of what the script does."""

import argparse
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--arg", type=str, help="Argument description")
    args = parser.parse_args()

    # Implementation here

if __name__ == "__main__":
    main()
```

## Acceptance Criteria

- Script executes without errors
- Script has proper documentation (docstring)
- Script follows Python best practices
- README.md updated if new script added
