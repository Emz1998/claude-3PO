import sys
from pathlib import Path
from datetime import datetime
from typing import Literal, get_args


sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.cache import get_cache  # type: ignore
from roadmap.utils import get_current_version, get_current, get_phase, get_milestone  # type: ignore

# CACHE PATHS
MAIN_CACHE_PATH = Path(".claude/hooks/cache.json")

MilestoneDir = Literal[
    "codebase-status",
    "reports",
    "decisions",
    "reports",
    "plans",
    "research",
    "revisions",
    "misc",
    "todos",
    "consults",
]


VALID_MILESTONE_DIR = get_args(MilestoneDir)

current_phase_id = get_current("phase")
current_milestone_id = get_current("milestone")

current_phase = get_phase(current_phase_id) or {}
current_milestone = get_milestone(current_milestone_id) or {}


current_phase_name = f"{current_phase_id}_{current_phase.get('name', '')}"
current_milestone_name = f"{current_milestone_id}_{current_milestone.get('name', '')}"

# BASE_PATH
BASE_PATH = Path(
    f"project/{get_current_version()}/{current_phase_name}/{current_milestone_name}"
)


def build_project_path(
    milestone_dir: MilestoneDir,
    file_name: str,
) -> Path:
    if milestone_dir not in VALID_MILESTONE_DIR:
        print(
            f"Invalid milestone directory: {milestone_dir}. List of valid milestone directories: {', '.join(VALID_MILESTONE_DIR)}"
        )
    return (
        BASE_PATH
        / milestone_dir
        / f"{file_name}_{get_cache('session_id', MAIN_CACHE_PATH)}_{datetime.now().strftime('%m%d%Y')}.md"
    )


if __name__ == "__main__":
    print(VALID_MILESTONE_DIR)
