# Release Plan JSON Schema

**Version:** 2.0.0

This document defines the structure for `release-plan.json` used in project execution tracking.

---

## Top-Level Structure

```json
{
  "product": "string",
  "vision": "string",
  "releases": []
}
```

- **product**: Product name
- **vision**: High-level product vision statement
- **releases**: Array of release versions, each containing epics

---

## Release

A release groups epics under a specific version milestone.

```json
{
  "version": "string",
  "name": "string",
  "target_date": "string",
  "epics": []
}
```

- **version**: Semantic version (e.g., "1.0.0")
- **name**: Release codename or label (e.g., "MVP")
- **target_date**: Target date or quarter (e.g., "2026-02-28" or "2026-Q2")
- **epics**: Epics within this release

---

## Epic

Epics are top-level groupings of related features within a release.

```json
{
  "id": "EPIC-NNN",
  "title": "string",
  "requirements": {
    "functional": [],
    "non_functional": []
  },
  "features": []
}
```

- **id**: Unique identifier (pattern: `EPIC-NNN`)
- **title**: Epic name
- **requirements**: Epic-level requirements split into functional and non-functional
- **features**: Features within this epic

---

## Functional Requirement

Defines what the system must do.

```json
{
  "id": "FR-NNN",
  "description": "string"
}
```

- **id**: `FR-NNN` format
- **description**: What the system must accomplish

---

## Non-Functional Requirement

Defines quality attributes and constraints.

```json
{
  "id": "NFR-NNN",
  "description": "string"
}
```

- **id**: `NFR-NNN` format
- **description**: Quality attribute or constraint that must be satisfied

---

## Feature

Features represent a deliverable capability. One feature maps to one or more user stories.

```json
{
  "id": "FEAT-NNN",
  "title": "string",
  "outcome": "string (optional)",
  "tdd": true,
  "success_criteria": [],
  "user_stories": []
}
```

- **id**: Unique identifier (pattern: `FEAT-NNN`)
- **title**: Feature name
- **outcome**: *(optional)* What this feature delivers
- **tdd**: Boolean flag indicating if Test-Driven Development applies
- **success_criteria**: Feature-level success verification (SC items)
- **user_stories**: User stories within this feature

---

## Success Criteria (Feature Level)

```json
{
  "id": "SC-NNN",
  "description": "string"
}
```

- **id**: `SC-NNN` format
- **description**: What must be true for the feature to be considered successful

---

## User Story

```json
{
  "id": "US-NNN",
  "story": "string",
  "context": "string",
  "acceptance_criteria": [],
  "tasks": []
}
```

- **id**: Unique identifier (pattern: `US-NNN`)
- **story**: User story (format: "As a [role], I want [goal] so that [benefit]")
- **context**: Background context and additional details
- **acceptance_criteria**: Story-level acceptance verification (AC items)
- **tasks**: Tasks that implement this user story

---

## Acceptance Criteria (User Story Level)

```json
{
  "id": "AC-NNN",
  "description": "string"
}
```

- **id**: `AC-NNN` format
- **description**: Specific testable condition that must be satisfied

---

## Task

```json
{
  "id": "TNNN",
  "description": "string",
  "dod": "string",
  "dependencies": []
}
```

- **id**: Unique identifier (pattern: `TNNN`)
- **description**: What the task accomplishes
- **dod**: Definition of Done - specific condition for task completion
- **dependencies**: `TNNN` IDs that must complete first

---

## ID Patterns

- **Epic**: `EPIC-NNN` (e.g., EPIC-001)
- **Functional Requirement**: `FR-NNN` (e.g., FR-001)
- **Non-Functional Requirement**: `NFR-NNN` (e.g., NFR-001)
- **Feature**: `FEAT-NNN` (e.g., FEAT-001)
- **User Story**: `US-NNN` (e.g., US-001)
- **Task**: `TNNN` (e.g., T001)
- **Success Criteria**: `SC-NNN` (e.g., SC-001)
- **Acceptance Criteria**: `AC-NNN` (e.g., AC-001)

---

## Completion Logic

- **Task**: Completed when its DoD is satisfied
- **User Story**: All tasks complete AND all acceptance_criteria met
- **Feature**: All user stories complete AND all success_criteria met
- **Epic**: All features complete AND all requirements (FR + NFR) verified
- **Release**: All epics complete
