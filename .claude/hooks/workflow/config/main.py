from pathlib import Path

CODE_EXTENSIONS = (
    "js",
    "jsx",
    "ts",
    "tsx",
    "json",
    "css",
    "scss",
    "less",
    "sass",
    "styl",
    "py",
    "java",
    "c",
    "cpp",
    "h",
    "hpp",
    "go",
    "php",
    "ruby",
    "swift",
)

TEST_EXTENSIONS = (
    "*_test.py",
    "*_test.js",
    "*.test.jsx",
    "*.test.ts",
    "*.test.tsx",
    "*.test.json",
    "*.test.css",
    "*.test.scss",
    "*.test.less",
    "*.test.sass",
    "*.test.styl",
)


PLAN_DIR = "home/user/.claude/plans"

READ_ONLY_TOOLS = ["Read", "Glob", "Grep"]

SAFE_COMMANDS = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "git status",
    "git diff",
    "git log",
    "git add .",
    "git commit -m",
    "pwd",
}

REVIEWER_AGENTS = ["code-reviewer", "plan-reviewer", "test-reviewer"]

CONFIDENCE_SCORE_THRESHOLD = 70
QUALITY_SCORE_THRESHOLD = 70
MAX_ITERATIONS = 3
