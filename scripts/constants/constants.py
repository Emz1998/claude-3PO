CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".rb",
    ".sh",
}


PR_COMMAND_PATTERNS = [r"\bgh\s+pr\s+create\b", r"\bgit\s+push\b"]
TEST_RUN_PATTERNS = [
    r"\bpytest\b",
    r"\bnpm\s+test\b",
    r"\byarn\s+test\b",
    r"\bgo\s+test\b",
    r"\bjest\b",
    r"\bvitest\b",
]
CI_CHECK_PATTERNS = [r"\bgh\s+pr\s+checks\b", r"\bgh\s+run\s+view\b"]

# ---------------------------------------------------------------------------
# Skill / story ID patterns
# ---------------------------------------------------------------------------
STORY_ID_PATTERN = r"\b([A-Z]{2,}-\d+)\b"


# ---------------------------------------------------------------------------
# Valid PR commands
# ---------------------------------------------------------------------------


PR_COMMANDS = [
    "git push",
    "git commit",
    "git add",
    "gh pr create",
    "gh pr merge",
    "gh pr close",
    "gh pr edit",
    "gh pr review",
    "gh pr comment",
]

CI_COMMANDS = [
    "gh run view",
    "gh run list",
    "gh run watch",
    "gh pr checks",
    "gh pr status",
]

INSTALL_COMMANDS = [
    "npm install",
    "yarn install",
    "yarn add",
    "go get",
    "go mod tidy",
    "pip install",
    "pip install -r",
    "gem install",
    "cargo add",
    "pnpm install",
    "pnpm add",
]

TEST_COMMANDS = [
    "pytest",
    "python -m pytest",
    "npm test",
    "npm run test",
    "yarn test",
    "yarn run test",
    "pnpm test",
    "go test",
    "jest",
    "vitest",
    "cargo test",
    "ruby -Itest",
    "rspec",
]

READ_ONLY_COMMANDS = [
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "wc",
    "file",
    "which",
    "whoami",
    "printenv",
    "date",
    "uname",
    "hostname",
    "df",
    "du",
    "free",
    "ps",
    "git status",
    "git log",
    "git diff",
    "git show",
    "git blame",
    "tree",
    "grep",
    "rg",
    "ag",
    "fd",
    "stat",
    "realpath",
    "dirname",
    "basename",
]

COMMANDS_MAP = {
    "install": INSTALL_COMMANDS,
    "write-tests": TEST_COMMANDS,
    "test-review": TEST_COMMANDS,
    "pr-create": PR_COMMANDS,
    "ci-check": CI_COMMANDS,
}

TEST_FILE_PATTERNS = [
    # JS / TS style
    "*.test.js",
    "*.test.ts",
    "*.test.jsx",
    "*.test.tsx",
    # Python style
    "test_*.py",
    "*_test.py",
    # Optional: JS test prefix style
    "test_*.js",
    "test_*.ts",
    "test_*.jsx",
    "test_*.tsx",
]


WRITE_COMMANDS = [
    "touch",
    "mkdir",
    "echo",
    "cat",
    "cp",
    "mv",
    "rm",
]
