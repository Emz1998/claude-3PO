# Sprint

**Sprint #:** `[X]`
**Milestone:** `[e.g. v.0.1.0]`
**Goal:** `[One sentence — what user-facing outcome does this sprint deliver?]`
**Due Date:** `[YYYY-MM-DD]`

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

| ID     | Type  | Title     | Points | Status | Blocked By |
| ------ | ----- | --------- | ------ | ------ | ---------- |
| US-NNN | Story | `[title]` | `[X]`  | Ready  | `-`        |
| TS-NNN | Tech  | `[title]` | `[X]`  | Ready  | `-`        |
| BG-NNN | Bug   | `[title]` | `[X]`  | Ready  | `-`        |
| SK-NNN | Spike | `[title]` | `[X]`  | Ready  | US-NNN     |

---

## Sprint Backlog

### User Stories

#### US-NNN: `[User story title]`

> **As a** `[user role]`, **I want** `[capability]` **so that** `[benefit]`.

**Labels:** `[e.g. setup, firebase, backend]`
**Points:** `[sum of task complexities]`
**Status:** `[Ready / In Progress / Done / Blocked]`
**TDD:** `[true / false]`
**Priority:** `[P0 / P1 / P2]`
**Is Blocking:** `[None / TS-NNN, US-NNN]`
**Blocked By:** `[None / SK-NNN]`
**Start Date:** `[YYYY-MM-DD or empty]`
**Target Date:** `[YYYY-MM-DD or empty]`

**Acceptance Criteria:**

- [ ] `[User-facing behavior that must be true when the story is done]`
- [ ] `[User-facing behavior]`
- [ ] `[User-facing behavior]`

**Tasks:**

- **T-001:** `[Task title]`
  - **Description:** `[What this task accomplishes]`
  - **Status:** `[Backlog / In Progress / In Review / Done / Blocked]`
  - **Priority:** `[P0 / P1 / P2]`
  - **Complexity:** `[S / M / L]`
  - **Labels:** `[e.g. backend, firebase, setup]`
  - **Blocked by:** `[None / T-XXX]`
  - **Acceptance Criteria:**
    - [ ] `[Specific, testable, implementation-level criterion]`
    - [ ] `[Specific criterion]`
    - [ ] `[Specific criterion]`
  - **Start date:** `[YYYY-MM-DD or empty]`
  - **Target date:** `[YYYY-MM-DD or empty]`

- **T-002:** `[Task title]`
  - **Description:** `[What this task accomplishes]`
  - **Status:** `[Backlog]`
  - **Priority:** `[P0 / P1 / P2]`
  - **Complexity:** `[S / M / L]`
  - **Labels:** `[e.g. database, firestore, backend]`
  - **Blocked by:** `[T-001]`
  - **Acceptance Criteria:**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Start date:**
  - **Target date:**

---

### Technical Stories

#### TS-NNN: `[Technical story title]`

> **As a** `[developer / system / codebase]`, **I need** `[what]` **so that** `[why]`.

**Labels:** `[e.g. infra, backend, refactor]`
**Points:** `[sum of task complexities]`
**Status:** `[Ready / In Progress / Done / Blocked]`
**TDD:** `[true / false]`
**Priority:** `[P0 / P1 / P2]`
**Is Blocking:** `[None / US-NNN]`
**Blocked By:** `[None / SK-NNN]`
**Start Date:** `[YYYY-MM-DD or empty]`
**Target Date:** `[YYYY-MM-DD or empty]`

**Acceptance Criteria:**

- [ ] `[Technical outcome that must be true when done]`
- [ ] `[Technical outcome]`

**Tasks:**

- **T-NNN:** `[Task title]`
  - **Description:** `[What this task accomplishes]`
  - **Status:** `[Backlog]`
  - **Priority:** `[P0 / P1 / P2]`
  - **Complexity:** `[S / M / L]`
  - **Labels:** `[e.g. setup, backend]`
  - **Blocked by:** `[None]`
  - **Acceptance Criteria:**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Start date:**
  - **Target date:**

---

### Bugs

#### BG-NNN: `[Short bug description]`

> **What's broken:** `[Observed behavior]`
> **Expected:** `[What should happen]`
> **Actual:** `[What happens instead]`
> **Reproduce:** `[Steps to trigger the bug]`

**Labels:** `[e.g. bugfix, testing, frontend]`
**Points:** `[sum of task complexities]`
**Status:** `[Ready / In Progress / Done / Blocked]`
**TDD:** `[true / false]`
**Priority:** `[P0 / P1 / P2]`
**Is Blocking:** `[None]`
**Blocked By:** `[None]`
**Start Date:** `[YYYY-MM-DD or empty]`
**Target Date:** `[YYYY-MM-DD or empty]`

**Acceptance Criteria:**

- [ ] `[Bug no longer reproduces following the steps above]`
- [ ] `[Regression test added]`

**Tasks:**

- **T-NNN:** `[Task title]`
  - **Description:** `[What this task accomplishes]`
  - **Status:** `[Backlog]`
  - **Priority:** `[P0 / P1 / P2]`
  - **Complexity:** `[S / M / L]`
  - **Labels:** `[e.g. bugfix, testing]`
  - **Blocked by:** `[None]`
  - **Acceptance Criteria:**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Start date:**
  - **Target date:**

---

### Spikes

#### SK-NNN: `[Research question]`

> **Investigate:** `[What we need to learn]`
> **To decide:** `[What decision this unblocks]`
> **Timebox:** `[Max hours — spikes must have a hard limit]`

**Labels:** `[e.g. spike, research, analysis]`
**Points:** `[S or M only — spikes should never be L]`
**Status:** `[Ready / In Progress / Done]`
**TDD:** `false`
**Priority:** `[P0 / P1 / P2]`
**Is Blocking:** `[None / TS-NNN]`
**Blocked By:** `[None]`
**Start Date:** `[YYYY-MM-DD or empty]`
**Target Date:** `[YYYY-MM-DD or empty]`

**Acceptance Criteria:**

- [ ] `[Decision documented in decisions.md]`
- [ ] `[Recommendation with pros/cons/tradeoffs]`
- [ ] `[Prototype or proof of concept (if applicable)]`

**Tasks:**

- **T-NNN:** `[Deliverable title]`
  - **Description:** `[What this task accomplishes]`
  - **Status:** `[Backlog]`
  - **Priority:** `[P1]`
  - **Complexity:** `[S / M]`
  - **Labels:** `[e.g. analysis, documentation]`
  - **Blocked by:** `[None]`
  - **Acceptance Criteria:**
    - [ ] `[Criterion]`
    - [ ] `[Criterion]`
  - **Start date:**
  - **Target date:**

> Spikes do NOT go through the QA / Code Reviewer pipeline.
> They produce a decision, not shippable code.
