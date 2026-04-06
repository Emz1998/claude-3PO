"""constants.py — All non-path workflow constants in one place."""

import re

# ---------------------------------------------------------------------------
# Phase sets
# ---------------------------------------------------------------------------
AGENT_ONLY_PHASES = {"explore", "plan"}
AGENT_PLUS_WRITE_PHASES = {"review"}
CODING_PHASES = {"write-tests", "write-code", "validate", "ci-check", "report"}
PLAN_ALLOWED_STOP_PHASES = {"present-plan", "completed", "failed"}

# ---------------------------------------------------------------------------
# Agent limits
# ---------------------------------------------------------------------------
EXPLORE_MAX = 3
RESEARCH_MAX = 2
PLAN_MAX = 1
PLAN_REVIEW_MAX = 3
TEST_REVIEWER_MAX = 3
QA_MAX = 1

# ---------------------------------------------------------------------------
# Review thresholds
# ---------------------------------------------------------------------------
PLAN_REVIEW_THRESHOLD = {"confidence": 80, "quality": 80}

# ---------------------------------------------------------------------------
# File type patterns
# ---------------------------------------------------------------------------
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

TEST_PATH_PATTERNS = [
    re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)"),
    re.compile(r"(^|/)(test_.*|.*_test)\.(py|js|ts|jsx|tsx)$"),
    re.compile(r"(^|/).*\.(test|spec)\.(js|jsx|ts|tsx)$"),
]

CODEBASE_MD = "CODEBASE.md"

# ---------------------------------------------------------------------------
# Bash command patterns
# ---------------------------------------------------------------------------
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
STORY_ID_PATTERN = re.compile(r"\b([A-Z]{2,}-\d+)\b")

# ---------------------------------------------------------------------------
# Plan template validation
# ---------------------------------------------------------------------------
REQUIRED_SECTIONS = [
    r"^##\s+Context",
    r"^##\s+(Approach|Steps)",
    r"^##\s+(Files to Modify|Critical Files)",
    r"^##\s+Verification",
]

# ---------------------------------------------------------------------------
# Domain whitelist
# ---------------------------------------------------------------------------
SAFE_DOMAINS = [
    "docs.python.org",
    "docs.anthropic.com",
    "developer.mozilla.org",
    "reactjs.org",
    "react.dev",
    "nextjs.org",
    "tailwindcss.com",
    "github.com",
    "stackoverflow.com",
    "pypi.org",
    "npmjs.com",
    "typescriptlang.org",
    "nodejs.org",
    "firebase.google.com",
    "supabase.com",
    "expo.dev",
    "reactnative.dev",
    "code.claude.com",
    "vercel.com",
    "medium.com",
    "web.dev",
    "developers.google.com",
    "css-tricks.com",
]
