from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.project import BASE_PATH, build_project_path  # type: ignore
from utils.cache import get_cache  # type: ignore

# CACHE PATHS
MAIN_CACHE_PATH = Path(".claude/hooks/cache.json")

# STATES PATHS
SUBAGENTS_STATE_PATH = Path(".claude/hooks/states/subagents.json")
MAIN_STATE_PATH = Path(".claude/hooks/states/main.json")
MAIN_AGENT_STATE_PATH = Path(".claude/hooks/states/subagents/main-agent.json")
CODING_PHASE_STATE_PATH = Path(".claude/hooks/states/phases/coding.json")


# REPORT_FILE_PATHS
CODEBASE_STATUS_REPORT_FILE_PATH = build_project_path

TODO_REPORT_FILE_PATH = build_project_path(
    "todos",
    "todo",
)

PLAN_REPORT_FILE_PATH = build_project_path(
    "plans",
    "plan",
)

CONSULT_REPORT_FILE_PATH = build_project_path(
    "consults",
    "consultation",
)

RESEARCH_REPORT_FILE_PATH = build_project_path(
    "research",
    f"research_{get_cache('session_id', MAIN_CACHE_PATH)}_{datetime.now().strftime('%m%d%Y')}.md",
)

CODE_REVISION_REPORT_FILE_PATH = build_project_path(
    "revisions",
    f"code-revision_{get_cache('session_id', MAIN_CACHE_PATH)}_{datetime.now().strftime('%m%d%Y')}.md",
)

MISC_REPORT_FILE_PATH = build_project_path(
    "misc",
    f"misc_{get_cache('session_id', MAIN_CACHE_PATH)}_{datetime.now().strftime('%m%d%Y')}.md",
)
