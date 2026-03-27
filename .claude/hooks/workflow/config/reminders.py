REMINDERS_TEMPLATES = [
    {
        "reminder_type": "code_review",
        "event": "PostToolUse",
        "label": "review",
    },
    {
        "reminder_type": "write_tests",
        "event": "PreToolUse",
        "tool_name": "write_tests",
        "tool_input_key": "file_path",
        "tool_input_value": "write-tests.md",
        "label": "write",
    },
    {
        "reminder_type": "write_code",
        "label": "write",
        "path": "write-code.md",
    },
    {
        "reminder_type": "test_review",
        "label": "review",
        "path": "test-review.md",
    },
    {
        "reminder_type": "code_refactor",
        "label": "refactor",
        "path": "code-refactor.md",
    },
    {
        "reminder_type": "test_refactor",
        "label": "refactor",
        "path": "test-refactor.md",
    },
    {
        "reminder_type": "plan_review",
        "label": "review",
        "path": "plan-review.md",
    },
    {
        "reminder_type": "plan_revision",
        "label": "revision",
        "path": "plan-revision.md",
    },
    {
        "reminder_type": "strategy_research",
        "label": "research",
        "path": "strategy-research.md",
    },
    {
        "reminder_type": "latest_docs_research",
        "label": "research",
        "path": "latest-docs-research.md",
    },
    {
        "reminder_type": "codebase_status",
        "label": "explore",
        "path": "codebase-status.md",
    },
]
