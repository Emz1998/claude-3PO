# Build Entry — PR-Aware Routing

## Context
`/build` currently finds stories with status "Ready" and launches parallel `/implement <story-id>` sessions. We want it to first check for open PRs — if any exist, launch `/review <pr-number>` sessions instead. `/review` is a built-in Claude Code skill that takes a PR number.

## Approach

### Modify `.claude/hooks/workflow/handlers/build_entry.py`

Add an `open_pr_numbers` property that calls `gh pr list` directly (auto-detects repo from git remote):

```python
import json

@property
def open_pr_numbers(self) -> list[int]:
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "number", "--limit", "100"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        prs = json.loads(result.stdout)
        return [pr["number"] for pr in prs]
    return []
```

Update `run()` to check PRs first:

```python
def run(self) -> None:
    if not self.validate_prompt():
        return

    activate_workflow()

    pr_numbers = self.open_pr_numbers
    if pr_numbers:
        prompts = [f"/review {n}" for n in pr_numbers]
    else:
        prompts = self.prompts  # existing /implement behavior

    if not prompts:
        return
    self.launch_sessions(prompts)
    Hook.advanced_output({"continue": False, "reason": "No further action required"})
```

## Files
- **Modify**: `.claude/hooks/workflow/handlers/build_entry.py` — add `open_pr_numbers`, update `run()`
- **Reference**: `github_project/pr_manager.py` — pattern reference for `gh pr list` usage

## Verification
1. Run tests: `python -m pytest .claude/hooks/workflow/tests/ -v`
2. Manual test: with open PRs, `/build` should generate `/review` prompts
3. Manual test: with no open PRs, `/build` should generate `/implement` prompts as before
