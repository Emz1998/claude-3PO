# Product Brief

**Project:** `[Project Name]`
**Version:** `[v1.0]`
**Last Updated:** `[YYYY-MM-DD]`
**Product Vision:** `[Link to product-vision.md — this brief is the tactical companion to the strategic vision]`

---

## One-Liner

> What is this product in one sentence? An executive, a developer, and a user should all understand it.

`[Product Name]` is a `[category]` that `[what it does]` for `[who]` so they can `[key benefit]`.

---

## Problem

### What's Broken Today?

`[2-3 sentences describing the specific pain point. Be concrete — what does the user currently do, how long does it take, and why is it frustrating?]`

### Evidence

> How do you know this is a real problem? List your sources.

| Source                       | What It Told You     |
| ---------------------------- | -------------------- |
| `[e.g. Personal experience]` | `[Specific insight]` |
| `[e.g. User interviews]`     | `[Specific insight]` |
| `[e.g. Market research]`     | `[Specific insight]` |
| `[e.g. Competitor gaps]`     | `[Specific insight]` |

---

## User Personas

> Define the specific users your Product Owner writes stories for.
> Each persona maps to a role in "As a `[role]`, I want..." stories.

### Primary Persona: `[Persona name]`

| Attribute        | Detail                                                      |
| ---------------- | ----------------------------------------------------------- |
| **Who**          | `[Role, background, demographics]`                          |
| **Context**      | `[When/where do they use this product?]`                    |
| **Goal**         | `[What are they trying to accomplish?]`                     |
| **Frustration**  | `[What's painful about their current approach?]`            |
| **Tech comfort** | `[Low / Medium / High]`                                     |
| **Story role**   | `[How they appear in user stories, e.g. "nursing student"]` |

### Secondary Persona: `[Persona name]` (if applicable)

| Attribute        | Detail                                           |
| ---------------- | ------------------------------------------------ |
| **Who**          | `[Role, background, demographics]`               |
| **Context**      | `[When/where do they use this product?]`         |
| **Goal**         | `[What are they trying to accomplish?]`          |
| **Frustration**  | `[What's painful about their current approach?]` |
| **Tech comfort** | `[Low / Medium / High]`                          |
| **Story role**   | `[How they appear in user stories]`              |

---

## Core User Journey

> How do the MVP features connect into one flow from the user's perspective?
> The Product Owner uses this to write story-level acceptance criteria.
> The QA Agent uses this during sprint close smoke tests.

```
[Map the end-to-end flow. Example:]

1. User opens app → [what they see]
       ↓
2. User does [action] → [what happens]
       ↓
3. User does [action] → [product responds with]
       ↓
4. User gets [outcome / value]
```

### Journey Narrative

`[Walk through the flow in 1 paragraph of plain language. This is what the smoke test validates — if a user can complete this journey, the MVP works.]`

---

## MVP Scope

### Features In

> These map to epics in backlog.md. Each feature becomes one or more user stories.

| #   | Feature          | Description                             | Epic     |
| --- | ---------------- | --------------------------------------- | -------- |
| 1   | `[Feature name]` | `[One sentence — what the user can do]` | `EP-NNN` |
| 2   | `[Feature name]` | `[One sentence]`                        | `EP-NNN` |
| 3   | `[Feature name]` | `[One sentence]`                        | `EP-NNN` |
| 4   | `[Feature name]` | `[One sentence]`                        | `EP-NNN` |

### Features Out (Explicitly Deferred)

> These are NOT forgotten — they're deliberately excluded from MVP.
> The Product Owner should never create stories for these until you move them in.

| Feature     | Why Not Yet              |
| ----------- | ------------------------ |
| `[Feature]` | `[Reason for deferring]` |
| `[Feature]` | `[Reason for deferring]` |
| `[Feature]` | `[Reason for deferring]` |

---

## Design Constraints

> Boundaries the Builder must operate within. Non-negotiable unless you update this document.

### Platform

| Constraint           | Value                                               |
| -------------------- | --------------------------------------------------- |
| Target platform      | `[e.g. Desktop only, Web, Mobile, Cross-platform]`  |
| Target OS            | `[e.g. macOS + Windows, or macOS-first for MVP]`    |
| Min screen size      | `[e.g. 1024x768, or "desktop only — no mobile"]`    |
| Offline support      | `[Yes / No / Partial — specify what works offline]` |
| Browser requirements | `[e.g. N/A (desktop app) or Chrome/Firefox/Safari]` |

### Performance

| Constraint           | Target                                |
| -------------------- | ------------------------------------- |
| App launch time      | `[e.g. < 3 seconds]`                  |
| Core action response | `[e.g. < 500ms for UI interactions]`  |
| AI feature response  | `[e.g. < 2 seconds]`                  |
| Max bundle size      | `[e.g. < 50MB for desktop installer]` |

### Data & Privacy

| Constraint           | Detail                                             |
| -------------------- | -------------------------------------------------- |
| Auth method          | `[e.g. Email/password, OAuth, none for MVP]`       |
| Data storage         | `[e.g. Cloud only, local only, hybrid]`            |
| Data ownership       | `[e.g. User owns all data, exportable]`            |
| Privacy requirements | `[e.g. No telemetry in MVP, FERPA considerations]` |

---

## Tech Stack

> Reference for the Builder and Code Reviewer. Detailed architecture lives in architecture.md.

| Layer          | Choice                      | Notes                       |
| -------------- | --------------------------- | --------------------------- |
| Frontend       | `[e.g. React + TypeScript]` |                             |
| Desktop/Mobile | `[e.g. Tauri v2]`           | `[if applicable]`           |
| Backend        | `[e.g. Firebase]`           | `[Auth + Firestore]`        |
| AI             | `[e.g. GPT API]`            | `[model, e.g. gpt-4o-mini]` |
| Testing        | `[e.g. Vitest]`             |                             |
| Linting        | `[e.g. ESLint + Prettier]`  |                             |

---

## Timeline & Sprint Mapping

> The Scrum Master uses this to calculate velocity targets and flag when you're off track.

| Sprint | Dates                  | Theme                           | Epics                      |
| ------ | ---------------------- | ------------------------------- | -------------------------- |
| 1      | `[YYYY-MM-DD → MM-DD]` | `[e.g. Foundation + core loop]` | `[EP-001, EP-002]`         |
| 2      | `[YYYY-MM-DD → MM-DD]` | `[e.g. Data + AI features]`     | `[EP-002, EP-003]`         |
| 3      | `[YYYY-MM-DD → MM-DD]` | `[e.g. AI features + study]`    | `[EP-003, EP-004]`         |
| 4      | `[YYYY-MM-DD → MM-DD]` | `[e.g. Polish + ship]`          | `[Bug fixes, integration]` |

**Total timeline:** `[X weeks]`
**Ship date:** `[YYYY-MM-DD]`

> This is a plan, not a promise. Adjust at each sprint close based on actual velocity.

---

## Success Criteria

### MVP Launch (Go / No-Go)

> What must be true to consider the MVP shippable?

- [ ] `[Core user journey is completable end-to-end]`
- [ ] `[App launches and runs reliably on target platform]`
- [ ] `[AI features respond within performance targets]`
- [ ] `[No critical bugs in primary user flow]`
- [ ] `[Definition of Done met for all shipped stories]`

### Post-Launch Validation

> How do you know the MVP is _working_ after launch?

| Signal                   | Target                    | How You'll Measure          |
| ------------------------ | ------------------------- | --------------------------- |
| `[e.g. User activation]` | `[X% complete core flow]` | `[e.g. Firebase analytics]` |
| `[e.g. Retention]`       | `[X% return in 7 days]`   | `[e.g. Firebase analytics]` |
| `[e.g. Qualitative]`     | `[Positive feedback]`     | `[e.g. User interviews]`    |

---

## Assumptions & Open Questions

> Things you believe to be true but haven't validated, and questions that need answers.
> Open questions become Spikes (SK-NNN) in the backlog.

### Assumptions

| #   | Assumption                                                       | Risk if Wrong                   |
| --- | ---------------------------------------------------------------- | ------------------------------- |
| 1   | `[e.g. Nursing students will use a desktop app for note-taking]` | `[Need to pivot to web/mobile]` |
| 2   | `[e.g. GPT-4o-mini is accurate enough for clinical definitions]` | `[Need better model or RAG]`    |
| 3   | `[e.g. Users will highlight terms manually]`                     | `[Need auto-detection]`         |

### Open Questions

| #   | Question                                              | Blocks              | Backlog Item |
| --- | ----------------------------------------------------- | ------------------- | ------------ |
| 1   | `[e.g. Which rich text editor library to use?]`       | `[EP-001 / US-001]` | `SK-NNN`     |
| 2   | `[e.g. What's the right GPT prompt for definitions?]` | `[EP-003 / US-005]` | `SK-NNN`     |

---

## How Agents Use This Document

| Agent         | Reads This For                                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Product Owner | Personas (story roles), MVP scope (which epics to pull), core journey (story-level AC), deferred features (what NOT to plan) |
| Builder       | Tech stack, design constraints, performance targets                                                                          |
| QA Agent      | Success criteria, performance targets (for acceptance criteria validation)                                                   |
| Code Reviewer | Tech stack, design constraints (to flag violations)                                                                          |
| Scrum Master  | Timeline + sprint mapping (velocity targets), success criteria (launch readiness)                                            |
