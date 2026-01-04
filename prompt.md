**Main Goal:** Revise the roadmap/resolver.py script based on the logic below in `Context` section

## Context

### Dependencies

- If one of the tasks is set to `in_progress` -> `phase` and `milestone` must be set to `in_progress`
- If one of the phases is set to `in_progress` -> `project` must be set to `in_progress`
- Tasks should only be set to `completed` if all acceptance criteria are set to `met`
- Milestones should only be set to `completed` if all tasks in the milestone are set to `completed` and if all success criteria are set to `met`
- Phases should only be set to `completed` if all milestones in the phase are set to `completed`
- Project should only be set to `completed` if all phases are set to `completed`
- If status has been changed but dependencies are not met, the resolver must auto correct the status to the correct value based on the dependencies

### Valid Statuses

**Phase**:

- `not_started`
- `in_progress`
- `completed`

**Milestone**:

- `not_started`
- `in_progress`
- `blocked`
- `completed`

**Task**:

- `not_started`
- `in_progress`
- `completed`
- `blocked`

**Project**:

- `not_started`
- `in_progress`
- `completed`

## Instructions

- The resolver must be triggered in every `/implement` skill call.

-
