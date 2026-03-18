!`python3 github_project/project_manager.py view $0`
!`python3 .claude/hooks/workflow/utils/workflow_initializer.py --session-id ${CLAUDE_SESSION_ID} --story-id $0`

# Multi-Session Workflow — Dry Run

End-to-end test of the workflow hooks system. This runs the actual workflow phases through Claude Code to verify hooks fire correctly.

**IMPORTANT: This is a TEST ONLY. Do not implement, write code, create PRs, or push anything. Instruct agents to do nothing.**

---

## Dry Run 1: Success Flow

### Create Task

1. Create tasks using `TaskCreate` tool
2. Add a dependency/`blocked by` to the task using `TaskUpdate` tool
3. Present a mock task to the user and ask for approval
4. State to the user if the test is successful if no blockers are triggered

### Pre Coding

Invoke the following agents in order:

1. `Explore`
2. `Plan`
3. `plan-reviewer`
4. Present a mock plan to the user and ask for approval
5. State to the user if the test is successful if no blockers are triggered

**IMPORTANT**:

- Instruct agents to do nothing except for `plan-reviewer`
- `plan-reviewer` should write a plan in `.claude/sessions/session_$CLAUDE_SESSION_ID/plans/plan.md`
- The plan should have a frontmatter with `confidence_score` and `quality_score`

### Coding

Invoke the following agents in order:

1. `test-engineer`
2. `test-reviewer`
3. `code-reviewer`
4. Present a mock code to the user and ask for approval
5. State to the user if the test is successful if no blockers are triggered

**IMPORTANT**:

- Instruct agents to do nothing except for `code-reviewer`
- `test-reviewer` should write a test-review report in `.claude/sessions/session_$CLAUDE_SESSION_ID/reviews/test-review.md`
- `code-reviewer` should write a code-review report in `.claude/sessions/session_$CLAUDE_SESSION_ID/reviews/code-review.md`
- The code-review report should have a frontmatter with `confidence_score` and `quality_score`
- Please follow the review loop that a hook suggest

### Create Pull Request

1. Invoke `/create-pr` skill to create a mock pull request
2. Invoke `/ci-check` skill to check if the pull request is passing the CI checks
3. Report to the user if the pull request is passing or failing the CI checks
4. Try to stop. If stop successfully, report to the user a summary of the dry run test
