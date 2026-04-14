from .write_guard import handle as write_guard
from .edit_guard import handle as edit_guard
from .command_guard import handle as command_guard
from .agent_guard import handle as agent_guard
from .webfetch_guard import handle as webfetch_guard
from .phase_guard import handle as phase_guard
from .agent_report_guard import handle as agent_report_guard
from .task_create_guard import handle as task_create_guard

TOOL_GUARDS = {
    "Write": write_guard,
    "Edit": edit_guard,
    "Bash": command_guard,
    "Agent": agent_guard,
    "WebFetch": webfetch_guard,
    "Skill": phase_guard,
    "TaskCreate": task_create_guard,
}

STOP_GUARDS = {
    "agent_report": agent_report_guard,
}
