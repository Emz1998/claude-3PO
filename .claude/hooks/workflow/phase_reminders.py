#!/usr/bin/env python3
"""Phase reminder content definitions for workflow context injection."""

PHASE_REMINDERS: dict[str, str] = {
    "explore": """
## Phase: EXPLORE
**Purpose:** Understand codebase structure and requirements before planning.

**Deliverables:**
- Read relevant source files and specs
- Identify dependencies and patterns
- Document findings for planning phase

**Key Focus:**
- Understand existing architecture
- Identify files that need modification
- Note any constraints or blockers

**Next Phase:** plan - Create implementation plan based on exploration findings.
""",
    "plan": """
## Phase: PLAN
**Purpose:** Create a detailed implementation plan based on exploration findings.

**Deliverables:**
- Write implementation plan to designated file
- Include file modifications, dependencies, and risks
- Define acceptance criteria

**Key Focus:**
- Clear, actionable steps
- Consider edge cases
- Identify testing requirements

**Next Phase:** plan-consult - Get plan reviewed before implementation.
""",
    "plan-consult": """
## Phase: PLAN-CONSULT
**Purpose:** Review and validate the implementation plan before proceeding.

**Deliverables:**
- Read and analyze the implementation plan
- Identify gaps, risks, or improvements
- Provide quality rating (1-10)

**Key Focus:**
- Completeness and feasibility
- Alignment with requirements
- Risk assessment

**Next Phase:** write_test - Begin TDD with failing tests.
""",
    "write_test": """
## Phase: WRITE_TEST (TDD Red)
**Purpose:** Create failing tests that define expected behavior.

**Deliverables:**
- Write test files in appropriate test directory
- Tests should fail initially (Red phase)
- Cover acceptance criteria from plan

**Key Focus:**
- Test-first approach
- Clear assertions
- Edge case coverage

**Next Phase:** review_test - Validate test quality before implementation.
""",
    "review_test": """
## Phase: REVIEW_TEST
**Purpose:** Validate test quality and coverage before implementation.

**Deliverables:**
- Read and analyze test files
- Check coverage of acceptance criteria
- Provide feedback on test quality

**Key Focus:**
- Test completeness
- Proper assertions
- Maintainability

**Next Phase:** implement - Write code to make tests pass.
""",
    "implement": """
## Phase: IMPLEMENT (TDD Green)
**Purpose:** Write minimal code to pass all failing tests.

**Deliverables:**
- Implement code changes as defined in plan
- All tests should pass (Green phase)
- Follow existing code patterns

**Key Focus:**
- Minimal implementation to pass tests
- Follow coding standards
- No over-engineering

**Next Phase:** code-review - Get implementation reviewed.
""",
    "code-review": """
## Phase: CODE-REVIEW
**Purpose:** Peer review the implementation for quality and correctness.

**Deliverables:**
- Review implementation files
- Check for security vulnerabilities
- Provide feedback and quality rating

**Key Focus:**
- Code quality and readability
- Security considerations
- Adherence to standards

**Next Phase:** refactor - Improve code while keeping tests green.
""",
    "refactor": """
## Phase: REFACTOR (TDD Refactor)
**Purpose:** Improve code quality while keeping all tests passing.

**Deliverables:**
- Refactor implementation for clarity and maintainability
- Ensure tests remain green
- Remove duplication and improve naming

**Key Focus:**
- Clean code principles
- DRY (Don't Repeat Yourself)
- Maintain test coverage

**Next Phase:** validate - Final validation before commit.
""",
    "validate": """
## Phase: VALIDATE
**Purpose:** Final validation to ensure everything is ready for commit.

**Deliverables:**
- Run all tests and linters
- Verify all acceptance criteria met
- Check for any regressions

**Key Focus:**
- All tests passing
- No linting errors
- Documentation complete

**Next Phase:** commit - Commit validated changes.
""",
    "commit": """
## Phase: COMMIT
**Purpose:** Commit validated changes with proper commit message.

**Deliverables:**
- Stage relevant files
- Create descriptive commit message
- Follow conventional commit format

**Key Focus:**
- Clear commit message
- Only include related changes
- Reference issue/milestone if applicable

**Workflow Complete:** Changes committed successfully.
""",
}


def get_phase_reminder(phase: str) -> str | None:
    """Get the reminder content for a given phase.

    Args:
        phase: The workflow phase name

    Returns:
        The reminder content string, or None if phase not found
    """
    return PHASE_REMINDERS.get(phase)
