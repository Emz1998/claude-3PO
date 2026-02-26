"""Project status schema for init_dir module."""

from pydantic import BaseModel


class Status(BaseModel):
    version: str = "v0.1.0"
    project_name: str = ""
    project_status: bool = False
    current_phase_num: int = 0
    current_phase: str = ""
    current_phase_status: bool = False
    current_milestone: str = ""
    current_milestone_status: bool = False
    total_phases: int = 0
    phases_completed: int = 0
    phases_remaining: int = 0
    total_milestones: int = 0
    milestones_completed: int = 0
    milestones_remaining: int = 0
    total_tasks: int = 0
    tasks_completed: int = 0
    tasks_remaining: int = 0
