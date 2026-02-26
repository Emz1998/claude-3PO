import json
import sys
from pathlib import Path
from typing import List, TypedDict, Any, Mapping

sys.path.insert(0, str(Path(__file__).parent))
from status import get_status, set_status  # type: ignore


class PhaseTemplate(TypedDict):
    phase_number: int
    phase_description: str
    milestone_number: str
    milestone_description: str
    goal: str
    tasks: str
    acceptance_criteria: str
    verification: str


def load_roadmap(roadmap_path: str) -> dict[str, Any]:
    roadmap = Path(roadmap_path)
    try:
        if not roadmap.exists():
            raise FileNotFoundError(f"Roadmap file not found: {roadmap}")
        roadmap_data = json.loads(roadmap.read_text())
    except Exception as e:
        raise Exception(f"Error loading roadmap: {e}")
    return roadmap_data


def load_template(template_path: str) -> str:
    template = Path(template_path)
    try:
        if not template.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        content = template.read_text()
    except Exception as e:
        raise Exception(f"Error loading template: {e}")
    return content


def fill_out_template(template: str, kwargs: Mapping[str, Any]) -> str:
    return template.format(**kwargs)


def parse_acceptance_criteria(acceptance_criteria_list: List[str]) -> str:
    return "\n".join([f"- [ ] {criterion}" for criterion in acceptance_criteria_list])


def parse_verification(verification_list: List[str]) -> str:
    return "\n".join([f"- {verification}" for verification in verification_list])


def parse_tasks(tasks_list: List[str]) -> str:
    return "\n".join(
        [f"- T{index + 1:03d}: {task}" for index, task in enumerate(tasks_list)]
    )


def main():
    # Load phase template
    phase_template = load_template(".claude/scripts/roadmap_filler/templates/phase.md")

    # Load roadmap
    version = get_status("version")
    roadmap_path = Path(f"project/{version}/release-plan/roadmap.json")
    roadmap_data = load_roadmap(str(roadmap_path))

    # Parse acceptance criteria
    acceptance_criteria_list = roadmap_data["acceptance_criteria"]
    acceptance_criteria = parse_acceptance_criteria(acceptance_criteria_list)

    # Parse verification
    verification_list = roadmap_data["verification"]
    verification = parse_verification(verification_list)

    # Parse tasks
    tasks_list = roadmap_data["tasks"]
    tasks = parse_tasks(tasks_list)

    milestone_number = get_status("current_milestone_num")
    phase_args = PhaseTemplate(
        {
            "phase_number": get_status("current_phase_num"),
            "phase_description": get_status("current_phase_description"),
            "milestone_number": f"{milestone_number:03d}",
            "milestone_description": get_status("current_milestone_description"),
            "goal": "Setup the development environment",
            "tasks": tasks,
            "acceptance_criteria": acceptance_criteria,
            "verification": verification,
        }
    )
    filled_template = fill_out_template(phase_template, phase_args)
    print(filled_template)


if __name__ == "__main__":
    main()
