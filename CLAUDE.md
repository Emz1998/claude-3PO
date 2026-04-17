# CLAUDE.md

## Goal

- Build Claude-3PO , a workflow system with guardrails that prevent claude from drifting.

## Rules

- **IMPORTANT**:If not in plan mode, present a miniplan first to the user before implementing changes.
- **IMPORTANT**: Stop and ask the user first for plan approval.
- **IMPORTANT**: Always do TDD when coding. Write/Revise tests first before implementing changes
- **IMPORTANT** Plan should always be higher level.
- **IMPORTANT**: Questions should be always asked using `AskUserQuestion` tool.
- Do not proceed on implementing changes without a plan and without user approval
- Do not implement tasks that are beyond the scope of your plan
- If you are not sure, stop and say "I'm not sure about this task"
- Do not overcomplicate stuff. Simple/Lean approach is better than complex one
- Find and create solutions based on the complexity of the task.
- Always validate your work either through tests, sample ui, running a bash command, etc. Never skip any review
- Identify the README in claude-3PO that is part of your task scope and update it.
- Always make task list to track your tasks
- Before git stashing, please consult with the user.

## Coding Style

- Max of 15 lines per function.
- Make it modular and reusable as much as possible.
- Write semantic and idiomatic code. Use clear and descriptive names for variables, functions, and classes.
- Prefer readability over complexity. Write code that is easy to understand and maintain.

### Python

- Include a readable docstring with the structure below:

```
    """
    Process a list of integers and optionally normalize the values.

    Args:
        data (list[int]): Input list of integers.
        normalize (bool): Whether to normalize values between 0 and 1.

    Returns:
        list[float]: Processed list of floats.

    Raises:
        ValueError: If `data` is empty.

    Example:
        >>> process_data([1, 2, 3], normalize=True)
        [0.0, 0.5, 1.0]

    """

```
