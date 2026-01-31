import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from utils import load_json, set_json, get_json  # type: ignore
from init_status import init_status  # type: ignore
from project_schema import Status  # type: ignore


SPEC_DIR = [
    "brainstorm-summary.md",
    "prd.md",
    "tech-specs.md",
    "ux.md",
]


RELEASE_PLAN_DIR = [
    "roadmap.json",
    "roadmap.md",
    "overview.md",
]

MILESTONE_DIR = [
    "decisions",
    "plans",
    "research",
    "codebase-status",
    "revisions",
    "reports",
    "misc",
    "status.json",
]


def build_project_dir(version: str, milestone_name: str) -> dict[str, Any]:
    project_dir: dict[str, Any] = {
        "project": [
            {
                version: {
                    "specs": SPEC_DIR,
                    "release-plan": RELEASE_PLAN_DIR,
                    "milestones": {
                        milestone_name: MILESTONE_DIR,
                    },
                }
            },
            "status.json",
        ],
    }
    return project_dir


def build_milestone_dir(milestone_name: str = "") -> dict[str, Any]:
    current_milestone = milestone_name or get_current_milestone()
    print(f"current_milestone: {current_milestone}")
    return {
        "milestones": {
            current_milestone: MILESTONE_DIR,
        },
    }


def get_version(product_file_path: str = "project/product/PRD.json") -> str:
    return get_json("current_version", file_path=product_file_path)


def get_current_milestone(file_path: str = "") -> str:
    version = get_version()
    try:
        file_path = file_path or f"project/{version}/release-plan/roadmap.json"
        summary = get_json("summary", file_path=file_path)
        current_milestone = summary.get("milestones", {}).get("current_milestone", {})
        return (
            f"{current_milestone.get('id', '')}_[{current_milestone.get('name', '')}]"
        )
    except Exception as e:
        print(f"Error getting current milestone: {e}")
        return "MS-001: [Not Specified]"


def get_current_phase(file_path: str = "") -> str:
    version = get_version()
    try:
        file_path = file_path or f"project/{version}/release-plan/roadmap.json"
        summary = get_json("summary", file_path=file_path)
        current_phase = summary.get("phases", {}).get("current_phase", {})
        return current_phase.get("name", "")
    except Exception as e:
        print(f"Error getting current phase: {e}")
        return "Phase 1: [Not Specified]"


def init_dir(dir_path: str) -> Path:
    path = Path(dir_path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    print(f"Successfully initialized directory: {path}")
    return path


def init_file(file_path: str) -> Path:
    path = Path(file_path)
    if not path.exists():
        path.touch()
    return path


def init(item: Any, project_path: str) -> str:
    if isinstance(item, str):
        if item.endswith((".json", ".md")):
            init_file(f"{project_path}{item}")
        else:
            init_dir(f"{project_path}{item}")
    elif isinstance(item, dict):
        for key, value in item.items():
            init_dir(f"{project_path}{key}")
            init(value, f"{project_path}{key}/")
    elif isinstance(item, list):
        for sub_item in item:
            init(sub_item, project_path)
    else:
        raise ValueError(f"Invalid item type: {type(item)}")
    return project_path


def init_version_dir(current_version: str) -> None:
    version_dir = f"project/{current_version}/"
    init_dir(version_dir)


def init_phase_dir(current_version: str) -> None:
    current_phase = get_current_phase()
    phase_dir = f"project/{current_version}/{current_phase}/"
    init_dir(phase_dir)


def init_milestone_dir(current_version: str) -> None:
    dir_path = f"project/{current_version}/"
    init_dir(dir_path)


def init_milestone_contents(
    current_version: str, current_milestone: str, current_phase: str
) -> None:

    dir_structure = MILESTONE_DIR
    init_dir("project")
    init_version_dir(current_version)
    init_phase_dir(current_version)
    init_milestone_dir(current_version)
    init(
        dir_structure,
        f"project/{current_version}/{current_phase}/{current_milestone}/",
    )


def main() -> bool:

    init_dir("project")
    current_milestone = get_current_milestone("project/status.json")
    current_version = get_version("project/product/PRD.json")
    project_dir = build_project_dir(
        version=current_version, milestone_name=current_milestone
    )
    init(project_dir, "")
    return True


def test():
    current_version = get_version("project/product/PRD.json")
    current_milestone = "MS-001: [Unknown]"
    current_phase = get_current_phase("project/status.json")
    init_milestone_contents(current_version, current_milestone, current_phase)
    print(current_version)


if __name__ == "__main__":
    test()
