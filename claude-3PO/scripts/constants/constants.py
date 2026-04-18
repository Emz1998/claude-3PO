"""Shared constants used across hooks, guards, validators, and the async batcher.

Layout overview:
    * ``CODE_EXTENSIONS`` — file extensions treated as "source code" by guards.
    * Regex patterns (``PR_COMMAND_PATTERNS``, ``TEST_RUN_PATTERNS``,
      ``CI_CHECK_PATTERNS``, ``STORY_ID_PATTERN``, ``SCORE_PATTERNS``,
      ``TABLE_PATTERN``) — used by hooks to classify Bash invocations and parse
      structured agent output.
    * Command lists (``PR_COMMANDS``, ``CI_COMMANDS``, ``INSTALL_COMMANDS``,
      ``TEST_COMMANDS``, ``READ_ONLY_COMMANDS``, ``WRITE_COMMANDS``) — keyed by
      phase via ``COMMANDS_MAP`` to gate which shell commands a phase may run.
    * File patterns (``PACKAGE_MANAGER_FILES``, ``TEST_FILE_PATTERNS``) —
      heuristics for locating dependency manifests and test files.
    * Specs grammar (``SPECS_*``) — markdown markers, ID regex template, and
      blockquote patterns the SpecsValidator uses to parse backlog.md.
"""


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

SCORE_PATTERNS = [
    r"{label}\s*(?:score|rating)?\s*(?:\*\*)?\s*[:=\-]?\s*(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
    r"{label}\s*(?:score|rating)?\s+(?:is\s+)?(?:\*\*)?\s*(\d+)(?:\s*/\s*100)?",
]

TABLE_PATTERN = r"^(\|.+\|[ \t]*\n)(\|[ \t]*[-:]+.*\|[ \t]*\n)((?:\|.+\|[ \t]*\n?)*)"


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
    "install-deps": INSTALL_COMMANDS,
    "write-tests": TEST_COMMANDS,
    "write-code": TEST_COMMANDS,
    "test-review": TEST_COMMANDS,
    "pr-create": PR_COMMANDS,
    "ci-check": CI_COMMANDS,
}

PACKAGE_MANAGER_FILES = [
    "package.json",
    "requirements.txt",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "pyproject.toml",
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


# ---------------------------------------------------------------------------
# Specs document grammar (shared across all specs validators)
# ---------------------------------------------------------------------------

# Markdown bold-label markers for story/task fields.
SPECS_FIELD_MARKERS = {
    "description": "**Description:**",
    "priority": "**Priority:**",
    "milestone": "**Milestone:**",
    "is_blocking": "**Is Blocking:**",
    "blocked_by": "**Blocked By:**",
    "status": "**Status:**",
    "complexity": "**Complexity:**",
    "depends_on": "**Depends on:**",
}

# Story/task ID regex; the prefix list lives in config.specs_valid_item_types.
SPECS_ID_REGEX_TEMPLATE = r"^{prefix}-\d+$"

# Blockquote format regexes keyed by backlog item type prefix (US/TS/SK/BG).
# Each value is the regex that the blockquote body of a story of that type
# must match — e.g. user stories must contain "**As a**", spikes must contain
# "**Investigate:**". Keys must align with config.specs_valid_item_types.
SPECS_BLOCKQUOTE_PATTERNS = {
    "US": r"\*\*As a\*\*",
    "TS": r"\*\*As a\*\*",
    "SK": r"\*\*Investigate:\*\*",
    "BG": r"\*\*What['\u2019]s broken:\*\*",
}

# Acceptance-criteria checkbox markers.
SPECS_AC_MARKERS = ("- [ ]", "- [x]")

# Prefixes used to detect unfilled template placeholders in metadata values.
SPECS_PLACEHOLDER_PREFIXES = ("[", "<")

# Heading that introduces the story/task list block in backlog.md.
SPECS_STORIES_HEADING = "Stories"
