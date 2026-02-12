# Sprint

**Project:** `[Project Name]`
**Sprint #:** `[X]`
**Goal:** `[One sentence — what user-facing outcome does this sprint deliver?]`
**Dates:** `[YYYY-MM-DD]` → `[YYYY-MM-DD]`
**Capacity:** `[Hours/days available this sprint]`

---

## Story Types

| Prefix | Type            | Format                                               | When to Use                                      |
| ------ | --------------- | ---------------------------------------------------- | ------------------------------------------------ |
| US-NNN | User Story      | As a `[role]`, I want `[what]` so that `[why]`       | User-facing feature or behavior                  |
| TS-NNN | Technical Story | As a `[dev/system]`, I need `[what]` so that `[why]` | Infrastructure, refactors, non-user-facing work  |
| BG-NNN | Bug             | `[What's broken]` — Expected: `[X]`, Actual: `[Y]`   | Defect in existing functionality                 |
| SK-NNN | Spike           | Investigate `[question]` to decide `[decision]`      | Research needed before committing to an approach |

---

## Sprint Overview

> Quick-glance table of everything in this sprint. Update statuses here daily.

| ID     | Type  | Epic       | Title     | Points | Status | Depends On | Blocked By |
| ------ | ----- | ---------- | --------- | ------ | ------ | ---------- | ---------- |
| US-NNN | Story | `[EP-NNN]` | `[title]` | `[X]`  | Todo   | `-`        |            |
| TS-NNN | Tech  | `-`        | `[title]` | `[X]`  | Todo   | `-`        |            |
| BG-NNN | Bug   | `-`        | `[title]` | `[X]`  | Todo   | `-`        |            |
| SK-NNN | Spike | `[EP-NNN]` | `[title]` | `[X]`  | Todo   | US-NNN     | US-NNN     |

**Total Points:** `[X]`

---

## Sprint Backlog

### User Stories

#### US-NNN: `[User story title]`

> **As a** `[user role]`, **I want** `[capability]` **so that** `[benefit]`.

**Epic:** `[EP-NNN]`  
**Priority:** `[Must / Should / Nice]`  
**Story Points:** `[Total: sum of task complexities]`  
**Depends on:** `[Which US/TS/SK/BG this user story depends on, if known]`
**Status:** `[Todo / In Progress / Done / Partial]`

**Acceptance Criteria (Story Level):**

- [ ] `[User-facing behavior that must be true when the story is done]`
- [ ] `[User-facing behavior]`
- [ ] `[User-facing behavior]`

**Tasks:**

- **T-001:** `[Task title]`
  - **Status:** `[Todo / In Progress / In Review / Done / Blocked]`
  - **Complexity:** `[S / M / L]` `(S=1, M=2, L=3 points)`
  - **Depends on:** `[None / TASK-XXX]`
  - **Acceptance Criteria (Task Level):**
    - [ ] `[Specific, testable, implementation-level criterion]`
    - [ ] `[Specific criterion]`
    - [ ] `[Specific criterion]`
  - **Files touched:** `[e.g. src/components/..., src/services/...]`
  - **QA loops:** `[0/3]`
  - **Code Review loops:** `[0/2]`
  - **Notes for Builder:** `[Context, gotchas, constraints, relevant decisions.md entries]`

- **T-002:** `[Task title]`
  - **Status:** `[Todo]`
  - **Complexity:** `[S / M / L]`
  - **Depends on:** `[TASK-001]`
  - **Acceptance Criteria (Task Level):**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Files touched:**
  - **QA loops:** `[0/3]`
  - **Code Review loops:** `[0/2]`
  - **Notes for Builder:**

---

### Technical Stories

#### TS-NNN: `[Technical story title]`

> **As a** `[developer / system / codebase]`, **I need** `[what]` **so that** `[why]`.

**Priority:** `[Must / Should / Nice]`
**Story Points:** `[Total]`  
**Depends on:** `[Which US/TS/SK/BG this technical story depends on, if known]`
**Status:** `[Todo / In Progress / Done / Partial]`

**Acceptance Criteria:**

- [ ] `[Technical outcome that must be true when done]`
- [ ] `[Technical outcome]`

**Tasks:**

- **T-NNN:** `[Task title]`
  - **Status:** `[Todo]`
  - **Complexity:** `[S / M / L]`
  - **Depends on:** `[None]`
  - **Acceptance Criteria (Task Level):**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Files touched:**
  - **QA loops:** `[0/3]`
  - **Code Review loops:** `[0/2]`
  - **Notes for Builder:**

---

### Bugs

#### BG-NNN: `[Short bug description]`

> **What's broken:** `[Observed behavior]`  
> **Expected:** `[What should happen]`  
> **Actual:** `[What happens instead]`  
> **Reproduce:** `[Steps to trigger the bug]`

**Severity:** `[Critical / Major / Minor]`  
**Found in:** `[Which story/task introduced it, if known]`  
**Story Points:** `[Total]`  
**Depends on:** `[Which US/TS/SK/BG this bug depends on, if known]`
**Status:** `[Todo / In Progress / Done]`

**Acceptance Criteria:**

- [ ] `[Bug no longer reproduces following the steps above]`
- [ ] `[Regression test added]`
- [ ] `[No side effects on related functionality]`

**Tasks:**

- **T-NNN:** `[Task title]`
  - **Status:** `[Todo]`
  - **Complexity:** `[S / M / L]`
  - **Depends on:** `[None]`
  - **Acceptance Criteria (Task Level):**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Files touched:**
  - **QA loops:** `[0/3]`
  - **Code Review loops:** `[0/2]`
  - **Notes for Builder:**

---

### Spikes

#### SK-NNN: `[Research question]`

> **Investigate:** `[What we need to learn]`
> **To decide:** `[What decision this unblocks]`
> **Timebox:** `[Max hours — spikes must have a hard limit]`

**Depends on:** `[Which US/TS this spike depends on, e.g. US-003]`  
**Status:** `[Todo / In Progress / Done]`  
**Points:** `[S or M only — spikes should never be L]`

**Deliverable:**

- [ ] `[Decision documented in decisions.md]`
- [ ] `[Recommendation with pros/cons/tradeoffs]`
- [ ] `[Prototype or proof of concept (if applicable)]`

> Spikes do NOT go through the QA / Code Reviewer pipeline.
> They produce a decision, not shippable code.

---

<!-- DO NOT INCLUDE THIS SECTION IN THE SPRINT DOCUMENT -->

<!-- ## Agent Routing by Story Type

| Story Type      | Product Owner | Builder | QA Agent | Code Reviewer | Scrum Master |
| --------------- | ------------- | ------- | -------- | ------------- | ------------ |
| User Story      | Creates       | Builds  | Reviews  | Reviews       | Tracks       |
| Technical Story | Creates       | Builds  | Reviews  | Reviews       | Tracks       |
| Bug             | Creates       | Fixes   | Reviews  | Reviews       | Tracks       |
| Spike           | Creates       | —       | —        | —             | Tracks       |

> Spikes bypass the build pipeline. They produce decisions, not code.
> All other types follow the full pipeline: Builder / npm run check / QA / Code Reviewer / commit. -->
