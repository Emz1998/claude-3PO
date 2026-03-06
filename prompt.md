Revise @github_project/project_manager.py and @github_project/sync_project.py the new issues json names issues_v2.json.

Here is the instructions:

- Stories and Tasks are issues in Github Projects.
- Tasks are subissues of Stories.
- Title should have the format of "{id}: {title}"
- Description should have the format of:

```
{description}

- [ ] {acceptance_criteria item}
- [ ] {acceptance_criteria item}
- ...

```

- The description represents the issue body

- Also, for sync_project, if the new issue number is created due to deduplication, then you must also update the issue number in the issues_v2.json file accordingly
- If labels dont exist, then it must be created.
- If fields dont exist, then it must be created.
- Complexity should only be present in tasks
- Points should only be present in stories
- For top level keys like "sprint", "milestone", "goal", "dates", "totalPoints", etc. Suggest where to place them in github projects

- Do TDD and do regression test too
- Explore and plan first
