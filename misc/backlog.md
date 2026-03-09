# Product Backlog

**Project:** `[Project Name]`
**Last Updated:** `[YYYY-MM-DD]`

<!-- > **Purpose:** Single prioritized list of everything left to build, organized by epics and stories.
> The Product Owner reads this to pull stories into sprints.
> You own the priority order. -->

---

## Priority Legend

- 🔴 **Must have** — MVP doesn't ship without it
- 🟡 **Should have** — significantly improves MVP but not blocking
- 🟢 **Nice to have** — post-MVP or if time allows

## ID Conventions

| Prefix | Type            | Example | Scope               |
| ------ | --------------- | ------- | ------------------- |
| EP-NNN | Epic            | EP-001  | Backlog (permanent) |
| US-NNN | User Story      | US-001  | Backlog → Sprint    |
| TS-NNN | Technical Story | TS-001  | Backlog → Sprint    |
| BG-NNN | Bug             | BG-001  | Backlog → Sprint    |
| SK-NNN | Spike           | SK-001  | Backlog → Sprint    |
| T-NNN  | Task            | T-001   | Sprint only         |

- All IDs are global and sequential within their prefix
- IDs are permanent — they follow a story from backlog through sprint to completion

---

## Epics Overview

| ID     | Epic          | Priority | Stories | Status      |
| ------ | ------------- | -------- | ------- | ----------- |
| EP-001 | `[Epic name]` | 🔴       | `[X]`   | Not started |
| EP-002 | `[Epic name]` | 🔴       | `[X]`   | Not started |
| EP-003 | `[Epic name]` | 🟡       | `[X]`   | Not started |
| EP-004 | `[Epic name]` | 🟢       | `[X]`   | Not started |

---

## Epic Details

### EP-001: `[Epic name]`

**Description:** `[What this epic delivers as a whole — 1-2 sentences]`
**Priority:** `[🔴 / 🟡 / 🟢]`
**Status:** `[Not started / In Progress / Done]`

| ID     | Type | Story                                           | Priority | Status      | Sprint | Notes         |
| ------ | ---- | ----------------------------------------------- | -------- | ----------- | ------ | ------------- |
| US-001 | US   | As a `[user]`, I want `[what]` so that `[why]`  | 🔴       | Not started |        |               |
| US-002 | US   | As a `[user]`, I want `[what]` so that `[why]`  | 🔴       | Not started |        |               |
| SK-001 | SK   | Investigate `[question]` to decide `[decision]` | 🔴       | Not started |        | Blocks US-002 |

---

### EP-002: `[Epic name]`

**Description:** `[What this epic delivers]`
**Priority:** `[🔴 / 🟡 / 🟢]`
**Status:** `[Not started / In Progress / Done]`

| ID     | Type | Story                                                | Priority | Status      | Sprint | Notes |
| ------ | ---- | ---------------------------------------------------- | -------- | ----------- | ------ | ----- |
| US-003 | US   | As a `[user]`, I want `[what]` so that `[why]`       | 🔴       | Not started |        |       |
| TS-001 | TS   | As a `[dev/system]`, I need `[what]` so that `[why]` | 🟡       | Not started |        |       |

---

## Tech Debt / Infrastructure

> Technical stories and infrastructure work that don't belong to a specific epic.
> Pull into sprints as capacity allows.

| ID     | Type | Story                                                | Priority | Status      | Sprint | Notes |
| ------ | ---- | ---------------------------------------------------- | -------- | ----------- | ------ | ----- |
| TS-NNN | TS   | As a `[dev/system]`, I need `[what]` so that `[why]` | 🟡       | Not started |        |       |
| TS-NNN | TS   | As a `[dev/system]`, I need `[what]` so that `[why]` | 🟢       | Not started |        |       |

---

## Bug Backlog

> Bugs discovered during development that aren't fixed in the current sprint.
> Prioritize at sprint planning — 🔴 bugs should be pulled into the next sprint.

| ID     | Bug                                    | Severity         | Found In  | Status      | Sprint | Notes |
| ------ | -------------------------------------- | ---------------- | --------- | ----------- | ------ | ----- |
| BG-NNN | `[What's broken — expected vs actual]` | `[🔴 / 🟡 / 🟢]` | `[US/TS]` | Not started |        |       |

---

## Completed

| ID  | Type | Epic | Story | Completed | Sprint |
| --- | ---- | ---- | ----- | --------- | ------ |
|     |      |      |       |           |        |

---

## Status Values

### Story Status

| Status      | Meaning                                        |
| ----------- | ---------------------------------------------- |
| Not started | In backlog, not yet pulled into a sprint       |
| In Sprint   | Currently in an active sprint (note which one) |
| Completed   | All tasks done, moved to Completed table       |
| Deferred    | Explicitly pushed to post-MVP or later         |

### Epic Status

| Status      | Meaning                                      |
| ----------- | -------------------------------------------- |
| Not started | No stories from this epic have been started  |
| In Progress | At least one story is In Sprint or Completed |
| Done        | All stories in the epic are Completed        |

---

## How This Document Flows Into Sprints

```
Epics (you define the big capabilities)
    │
    ▼
Stories within epics — US, TS, SK, BG (you prioritize)
    │
    ▼
Product Owner reads backlog
    │
    ▼
Pulls stories into sprint.md
(story keeps its ID: US-NNN, TS-NNN, BG-NNN, SK-NNN)
    │
    ▼
Breaks each story into T-NNN tasks
(except Spikes — they produce decisions, not tasks)
    │
    ▼
You approve the sprint plan
    │
    ▼
Backlog updated:
  - In-sprint stories: Status → "In Sprint", Sprint column filled
  - Completed stories: moved to Completed table
  - Epic status updated when all its stories are done
  - New bugs added to Bug Backlog as discovered
  - New stories added to bottom of their epic
```

### Rules

- Stories use their type-specific format (US/TS/BG/SK), matching sprint.md
- A user story or technical story can only belong to one epic
- Bugs reference the story they were found in (if known)
- Spikes reference which story they unblock
- Don't add task-level detail here — that's the Product Owner's job during sprint planning
- Reprioritize at every sprint close based on Scrum Master recommendations
- 🔴 bugs take priority over 🟡 stories in the next sprint
