# Product Backlog

**Project:** `[Project Name]`
**Last Updated:** `[YYYY-MM-DD]`

---

## Priority Legend

- **P0** — MVP doesn't ship without it
- **P1** — significantly improves MVP but not blocking
- **P2** — post-MVP or if time allows

## ID Conventions

| Prefix | Type            | Example | Scope            |
| ------ | --------------- | ------- | ---------------- |
| US-NNN | User Story      | US-001  | Backlog → Sprint |
| TS-NNN | Technical Story | TS-001  | Backlog → Sprint |
| SK-NNN | Spike           | SK-001  | Backlog → Sprint |

- All IDs are global and sequential within their prefix
- IDs are permanent — they follow a story from backlog through sprint to completion

---

## Stories

### US-001: `[User story title]`

> **As a** `[user role]`, **I want** `[capability]` **so that** `[benefit]`.

**Description:** `[Brief description of the story]`
**Priority:** `[P0 / P1 / P2]`
**Milestone:** `[e.g. v.0.1.0]`
**Is Blocking:** `[None / TS-NNN, US-NNN]`
**Blocked By:** `[None / SK-NNN]`

**Acceptance Criteria:**

- [ ] `[User-facing behavior that must be true when the story is done]`
- [ ] `[User-facing behavior]`

---

### US-002: `[User story title]`

> **As a** `[user role]`, **I want** `[capability]` **so that** `[benefit]`.

**Description:** `[Brief description of the story]`
**Priority:** `[P0 / P1 / P2]`
**Milestone:** `[e.g. v.0.1.0]`
**Is Blocking:** `[None]`
**Blocked By:** `[SK-001]`

**Acceptance Criteria:**

- [ ] `[User-facing behavior]`
- [ ] `[User-facing behavior]`

---

### SK-001: `[Research question]`

> **Investigate:** `[What we need to learn]`
> **To decide:** `[What decision this unblocks]`

**Description:** `[Brief description of the spike]`
**Priority:** `[P0 / P1 / P2]`
**Milestone:** `[e.g. v.0.1.0]`
**Is Blocking:** `[US-002]`
**Blocked By:** `[None]`

**Acceptance Criteria:**

- [ ] `[Decision documented]`
- [ ] `[Recommendation with pros/cons/tradeoffs]`

---

### TS-001: `[Technical story title]`

> **As a** `[developer / system]`, **I need** `[what]` **so that** `[why]`.

**Description:** `[Brief description of the technical story]`
**Priority:** `[P0 / P1 / P2]`
**Milestone:** `[e.g. v.0.1.0]`
**Is Blocking:** `[None]`
**Blocked By:** `[None]`

**Acceptance Criteria:**

- [ ] `[Technical outcome that must be true when done]`
- [ ] `[Technical outcome]`

---

### BG-001: `[Short bug description]`

> **What's broken:** `[Observed behavior]`
> **Expected:** `[What should happen]`
> **Actual:** `[What happens instead]`

**Description:** `[Brief description of the bug]`
**Priority:** `[P0 / P1 / P2]`
**Milestone:** `[e.g. v.0.1.0]`
**Is Blocking:** `[None]`
**Blocked By:** `[None]`

**Acceptance Criteria:**

- [ ] `[Bug no longer reproduces]`
- [ ] `[Regression test added]`
