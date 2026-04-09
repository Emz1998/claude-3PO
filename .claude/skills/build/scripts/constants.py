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


VALID_PR_COMMANDS = [
    "git push",
    "git pull",
    "git fetch",
    "git merge",
    "git rebase",
    "git reset",
    "git checkout",
    "git switch",
    "git commit",
]

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
