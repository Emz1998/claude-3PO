#

from pathlib import Path

from roadmap.utils import get_current, get_current_version, get_phase, get_milestone

VALID_MILESTONE_DIR = [
    "codebase-status",
    "reports" "decisions",
    "reports",
    "plans",
    "research",
    "revisions",
    "misc",
]

current_phase = get_phase() or {}
current_milestone = get_milestone() or {}

current_phase_name = f"{current_phase.get('id', '')}_{current_phase.get('name', '')}"
current_milestone_name = (
    f"{current_milestone.get('id', '')}_{current_milestone.get('name', '')}"
)

# BASE_PATH
BASE_PATH = Path(
    f"project/{get_current_version()}/{current_phase_name}/{current_milestone_name}"
)


def build_project_path(
    milestone_dir: str,
    file_name: str,
) -> Path:
    if milestone_dir not in VALID_MILESTONE_DIR:
        print(
            f"Invalid milestone directory: {milestone_dir}. List of valid milestone directories: {', '.join(VALID_MILESTONE_DIR)}"
        )
    return BASE_PATH / milestone_dir / file_name
