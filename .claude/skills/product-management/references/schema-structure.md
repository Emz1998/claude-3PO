# Product Schema Documentation

**Version:** 1.0
**Last Updated:** 2025-12-21

This document defines the JSON schema for the `product.json` file used to manage product definitions, versioning, and feature specifications.

---

## Root Structure

| Field             | Type   | Required | Description                                          |
| ----------------- | ------ | -------- | ---------------------------------------------------- |
| `current_version` | string | Yes      | The current development version (e.g., `"v0.1.0"`)   |
| `stable_version`  | string | Yes      | The target stable release version (e.g., `"v1.0.0"`) |
| `overview`        | object | Yes      | High-level product information                       |
| `versions`        | array  | Yes      | List of version releases with features               |
| `tech_stack`      | array  | Yes      | Technologies used in the project                     |
| `metadata`        | object | Yes      | File metadata for tracking changes                   |

---

## Overview Object

The `overview` object contains the product's strategic information.

| Field              | Type          | Required | Description                                                               |
| ------------------ | ------------- | -------- | ------------------------------------------------------------------------- |
| `name`             | string        | Yes      | Full product name                                                         |
| `type`             | string        | Yes      | Product type (e.g., `"web-application"`, `"mobile-app"`, `"desktop-app"`) |
| `elevator_pitch`   | string        | Yes      | Concise product description (1-2 sentences)                               |
| `industry_problem` | string        | Yes      | The problem this product solves                                           |
| `solutions`        | array[string] | Yes      | List of solution approaches                                               |
| `goals`            | array[string] | Yes      | Measurable product goals                                                  |

### Example

```json
{
  "overview": {
    "name": "Product Name",
    "type": "web-application",
    "elevator_pitch": "A brief description of the product...",
    "industry_problem": "The problem being solved...",
    "solutions": ["Solution approach 1", "Solution approach 2"],
    "goals": ["Goal 1 with measurable target", "Goal 2 with measurable target"]
  }
}
```

---

## Versions Array

Each version entry represents a release with its associated features.

| Field          | Type   | Required | Description                                                                   |
| -------------- | ------ | -------- | ----------------------------------------------------------------------------- |
| `version`      | string | Yes      | Semantic version number (e.g., `"v0.1.0"`)                                    |
| `release_date` | string | Yes      | Target release date (ISO 8601: `"YYYY-MM-DD"`)                                |
| `status`       | string | Yes      | Release status: `"not_started"`, `"in_progress"`, `"completed"`, `"released"` |
| `features`     | array  | Yes      | List of features in this version                                              |

### Example

```json
{
  "version": "v0.1.0",
  "release_date": "2025-12-21",
  "status": "not_started",
  "features": []
}
```

---

## Feature Object

Features are the primary unit of work within each version.

| Field              | Type   | Required | Description                                |
| ------------------ | ------ | -------- | ------------------------------------------ |
| `id`               | string | Yes      | Unique feature identifier (e.g., `"F001"`) |
| `name`             | string | Yes      | Feature name                               |
| `description`      | string | Yes      | Detailed feature description               |
| `user_stories`     | array  | Yes      | List of user stories                       |
| `requirements`     | object | Yes      | Functional and non-functional requirements |
| `dependencies`     | array  | Yes      | External dependencies                      |
| `risks`            | array  | Yes      | Identified risks                           |
| `success_criteria` | array  | Yes      | Criteria for feature completion            |

### Example

```json
{
  "id": "F001",
  "name": "Notification System",
  "description": "A system that allows users to receive notifications...",
  "user_stories": [],
  "requirements": {},
  "dependencies": [],
  "risks": [],
  "success_criteria": []
}
```

---

## User Story Object

User stories define functionality from the user's perspective.

| Field                 | Type   | Required | Description                                                                     |
| --------------------- | ------ | -------- | ------------------------------------------------------------------------------- |
| `id`                  | string | Yes      | Unique identifier (e.g., `"US-001"`)                                            |
| `title`               | string | Yes      | Short story title                                                               |
| `story`               | string | Yes      | Full user story in format: "As a [role], I want to [action], so that [benefit]" |
| `acceptance_criteria` | array  | Yes      | List of acceptance criteria                                                     |

### Acceptance Criteria Object

| Field      | Type   | Required | Description                                                              |
| ---------- | ------ | -------- | ------------------------------------------------------------------------ |
| `id`       | string | Yes      | Unique identifier (e.g., `"AC-001"`)                                     |
| `criteria` | string | Yes      | Gherkin-style criteria: "Given [context], when [action], then [outcome]" |

### Example

```json
{
  "id": "US-001",
  "title": "Receive Notifications",
  "story": "As a user, I want to receive notifications for new predictions and updates.",
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "criteria": "Given I am a user, when I visit the home page, then I should see a notification system."
    }
  ]
}
```

---

## Requirements Object

Requirements are split into functional and non-functional categories.

| Field            | Type  | Required | Description                         |
| ---------------- | ----- | -------- | ----------------------------------- |
| `functional`     | array | Yes      | List of functional requirements     |
| `non_functional` | array | Yes      | List of non-functional requirements |

### Requirement Item

| Field         | Type   | Required | Description                                         |
| ------------- | ------ | -------- | --------------------------------------------------- |
| `id`          | string | Yes      | Unique identifier (e.g., `"FR-001"` or `"NFR-001"`) |
| `description` | string | Yes      | Requirement description                             |

### Example

```json
{
  "requirements": {
    "functional": [
      {
        "id": "FR-001",
        "description": "User should be able to receive notifications."
      }
    ],
    "non_functional": [
      {
        "id": "NFR-001",
        "description": "The system should handle 1000 concurrent users."
      }
    ]
  }
}
```

---

## Dependency Object

Dependencies track external systems, APIs, or services required.

| Field        | Type   | Required | Description                        |
| ------------ | ------ | -------- | ---------------------------------- |
| `id`         | string | Yes      | Unique identifier (e.g., `"D001"`) |
| `dependency` | string | Yes      | Name of the dependency             |
| `assumption` | string | Yes      | Assumptions about this dependency  |

### Example

```json
{
  "id": "D001",
  "dependency": "Free NBA Stats API",
  "assumption": "The API is free and accessible."
}
```

---

## Risk Object

Risks identify potential issues and mitigation strategies.

| Field         | Type   | Required | Description                               |
| ------------- | ------ | -------- | ----------------------------------------- |
| `id`          | string | Yes      | Unique identifier (e.g., `"R001"`)        |
| `title`       | string | Yes      | Short risk title                          |
| `overview`    | string | Yes      | Risk description                          |
| `impact`      | string | Yes      | Impact if risk materializes               |
| `probability` | string | Yes      | Likelihood: `"Low"`, `"Medium"`, `"High"` |
| `mitigation`  | string | Yes      | Mitigation strategy                       |

### Example

```json
{
  "id": "R001",
  "title": "API Rate Limited",
  "overview": "The API may be rate limited.",
  "impact": "The system will be unable to access the API.",
  "probability": "High",
  "mitigation": "We will implement a caching strategy to minimize API calls."
}
```

---

## Success Criteria Object

Success criteria define measurable outcomes for feature completion.

| Field         | Type   | Required | Description                          |
| ------------- | ------ | -------- | ------------------------------------ |
| `id`          | string | Yes      | Unique identifier (e.g., `"SC-001"`) |
| `title`       | string | Yes      | Short criteria title                 |
| `description` | string | Yes      | Detailed criteria description        |

### Example

```json
{
  "id": "SC-001",
  "title": "API Access Verified",
  "description": "The system will be able to access the API."
}
```

---

## Tech Stack Array

A simple array of strings listing technologies used.

### Example

```json
{
  "tech_stack": ["Next.js", "React", "Tailwind CSS", "TypeScript", "Supabase"]
}
```

---

## Metadata Object

Tracks file modification history.

| Field          | Type   | Required | Description                                               |
| -------------- | ------ | -------- | --------------------------------------------------------- |
| `last_updated` | string | Yes      | Last modification date (ISO 8601: `"YYYY-MM-DD"`)         |
| `updated_by`   | string | Yes      | Name or identifier of the person who made the last update |

### Example

```json
{
  "metadata": {
    "last_updated": "2025-12-21",
    "updated_by": "John Doe"
  }
}
```

---

## ID Naming Conventions

| Prefix | Entity                     | Example              |
| ------ | -------------------------- | -------------------- |
| `F`    | Feature                    | `F001`, `F002`       |
| `US`   | User Story                 | `US-001`, `US-002`   |
| `AC`   | Acceptance Criteria        | `AC-001`, `AC-002`   |
| `FR`   | Functional Requirement     | `FR-001`, `FR-002`   |
| `NFR`  | Non-Functional Requirement | `NFR-001`, `NFR-002` |
| `D`    | Dependency                 | `D001`, `D002`       |
| `R`    | Risk                       | `R001`, `R002`       |
| `SC`   | Success Criteria           | `SC-001`, `SC-002`   |

---

## Status Values

### Version Status

| Value         | Description                                |
| ------------- | ------------------------------------------ |
| `not_started` | Version work has not begun                 |
| `in_progress` | Version is currently being developed       |
| `completed`   | All features are complete, pending release |
| `released`    | Version has been deployed to production    |

### Risk Probability

| Value    | Description                         |
| -------- | ----------------------------------- |
| `Low`    | Unlikely to occur (<30% chance)     |
| `Medium` | Possible occurrence (30-60% chance) |
| `High`   | Likely to occur (>60% chance)       |

---

## Validation Rules

1. **Version Format**: Must follow semantic versioning with `v` prefix (e.g., `v1.0.0`)
2. **Date Format**: All dates must use ISO 8601 format (`YYYY-MM-DD`)
3. **ID Uniqueness**: All IDs must be unique within their scope
4. **Required Arrays**: Empty arrays `[]` are valid, but the field must be present
5. **Feature Ordering**: Features within a version should be ordered by priority
