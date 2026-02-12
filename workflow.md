# NEXLY RN — Complete Workflow: Documentation to Execution

> This is your master reference for how everything connects.
> Read this once, then use it as a checklist until the process is muscle memory.

---

## The Big Picture

```
PHASE 1          PHASE 2           PHASE 3              PHASE 4           PHASE 5
Foundation   →   Sprint Plan   →   Build Loop       →   Sprint Close  →   Next Sprint
(once)           (every 2-3 days)  (daily)              (every 2-3 days)  (repeat)

  You               You +             You +                You +             You +
  alone             Product           Builder +            Scrum Master +    Product
                    Owner             QA Agent +           You               Owner
                                      Code Reviewer +
                                      Scrum Master
```

### Your 5 Agents

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENT            │  SCRUM ROLE       │  JOB                    │
├─────────────────────────────────────────────────────────────────┤
│  Product Owner    │  Product Owner    │  Backlog + sprint plan  │
│  Builder          │  Dev Team         │  Writes code            │
│  QA Agent         │  Dev Team (QA)    │  Acceptance criteria    │
│  Code Reviewer    │  Dev Team (Sr.)   │  Standards compliance   │
│  Scrum Master     │  Scrum Master     │  Daily tracking +       │
│                   │                   │  sprint close           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Do Once, Maintain Over Time)

**Goal:** Establish the documents that give your AI agents project awareness.

**Time:** 2-3 hours, one time.

### Steps

```
1.1  Fill out product-brief.md
     └─ Define MVP scope, target user, success criteria
     └─ This is your north star — agents reference it for prioritization

1.2  Fill out architecture.md
     └─ Draw your system diagram
     └─ Define data models
     └─ Document directory structure
     └─ List external dependencies
     └─ ⚠️ UPDATE THIS whenever architecture changes

1.3  Fill out coding-standards.md
     └─ Naming conventions, file organization
     └─ Testing policy
     └─ AI-specific rules (prompt storage, response validation)

1.4  Fill out definition-of-done.md
     └─ Your quality gate — keep it short and strict

1.5  Populate backlog.md
     └─ List every feature you can think of
     └─ Assign priority: 🔴 Must / 🟡 Should / 🟢 Nice
     └─ Don't worry about task-level detail yet — that's the Product Owner's job

1.6  Set up npm run check
     └─ tsc --noEmit && eslint src/ && vitest run
     └─ This is your automated quality gate — nothing ships without it
```

### Outputs

```
/docs
  ✅ product-brief.md        (filled)
  ✅ architecture.md          (filled)
  ✅ coding-standards.md      (filled)
  ✅ definition-of-done.md    (filled)
  ✅ decisions.md              (starter entries)

/workflow
  ✅ backlog.md               (populated with features)
```

### Rule

**Do NOT start building until Phase 1 is complete.** These documents are the context layer your agents depend on. Skipping this is like onboarding a new developer with zero documentation — they'll produce inconsistent, misaligned work.

---

## Phase 2: Sprint Planning (Every 2-3 Days)

**Goal:** Convert a sprint goal into structured, buildable tasks.

**Time:** 30-45 minutes.

**Agent:** Product Owner

### Steps

```
2.1  Define your sprint goal
     └─ One sentence: what's the outcome?
     └─ Example: "Working note editor with create, edit, delete, and persistence"

2.2  Gather context for the Product Owner
     └─ Open the Product Owner prompt template (workflow/prompts/product-owner.md)
     └─ Attach these files:
        ├─ product-brief.md
        ├─ architecture.md
        ├─ coding-standards.md
        ├─ definition-of-done.md
        ├─ backlog.md
        └─ retro.md (if past Sprint 1)
     └─ Paste your sprint goal
     └─ If Sprint 2+, paste the Sprint Summary from the previous sprint

2.3  Run the Product Owner
     └─ Submit to Claude (fresh session)
     └─ Product Owner produces 4-8 structured tasks with:
        ├─ Acceptance criteria
        ├─ Complexity estimates
        ├─ Dependencies
        └─ Builder notes

2.4  Review and adjust
     └─ Are tasks right-sized? (Nothing bigger than L)
     └─ Are acceptance criteria specific and testable?
     └─ Is the total load realistic for your available hours?
     └─ Reorder if needed
     └─ Remove anything too ambitious — push to backlog

2.5  Save as sprint.md
     └─ This is your source of truth for the sprint

2.6  Update backlog.md
     └─ Mark items that are now in the sprint
```

### Outputs

```
  ✅ sprint.md                (populated with tasks)
  ✅ backlog.md               (updated — sprint items marked)
```

### Common Mistakes

- Sprint goal too vague → Product Owner produces vague tasks → Builder produces vague code
- Too many tasks → you carry over half the sprint → demoralizing
- Skipping the review step → you build tasks that don't make sense

---

## Phase 3: Build Loop (Daily)

**Goal:** Execute tasks one at a time with quality gates at every step.

**Time:** Bulk of your working hours.

**Agents:** Builder (Claude Code) + QA Agent + Code Reviewer + Scrum Master (end of day)

### The Daily Rhythm

```
┌─────────────────────────────────────┐
│          MORNING (15 min)           │
│                                     │
│  1. Open sprint.md                  │
│  2. Check: anything blocked?        │
│  3. Pick the next Todo task         │
│     (respect dependency order)      │
│  4. Read its acceptance criteria    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│          BUILD CYCLE (per task)         │
│                                         │
│  ┌───────────────────────────────┐      │
│  │ STEP A: Feed task to Builder  │      │
│  │                               │      │
│  │ Give Claude Code:             │      │
│  │ • Task title + description    │      │
│  │ • Acceptance criteria         │      │
│  │ • Relevant architecture.md    │      │
│  │   sections                    │      │
│  │ • coding-standards.md         │      │
│  │ • Builder notes from sprint   │      │
│  └────────────┬──────────────────┘      │
│               │                         │
│               ▼                         │
│  ┌───────────────────────────────┐      │
│  │ STEP B: Run npm run check     │      │
│  │                               │      │
│  │ Types pass?     ✅ / ❌       │      │
│  │ Lint clean?     ✅ / ❌       │      │
│  │ Tests pass?     ✅ / ❌       │      │
│  │                               │      │
│  │ If ❌ → fix before review     │      │
│  └────────────┬──────────────────┘      │
│               │                         │
│               ▼                         │
│  ┌───────────────────────────────┐      │
│  │ STEP C: Run QA Agent          │      │
│  │                               │      │
│  │ "Does it work?"               │      │
│  │                               │      │
│  │ Give Claude (fresh session):  │      │
│  │ • qa-agent.md prompt          │      │
│  │ • Task spec from sprint.md    │      │
│  │ • npm run check output        │      │
│  │ • Code diff / new files       │      │
│  │                               │      │
│  │ Checks each acceptance        │      │
│  │ criterion: met / not met      │      │
│  └────────────┬──────────────────┘      │
│               │                         │
│          ┌────▼────┐                    │
│          │ VERDICT │                    │
│          └────┬────┘                    │
│          ┌────┴────┐                    │
│          │         │                    │
│       ✅ PASS   ❌ FAIL                 │
│          │         │                    │
│          │         ▼                    │
│          │   ┌──────────────┐           │
│          │   │ Feed issues  │           │
│          │   │ to Builder   │           │
│          │   │ Loop +1      │           │
│          │   │ (max 3)      │           │
│          │   └──────────────┘           │
│          │                              │
│          ▼                              │
│  ┌───────────────────────────────┐      │
│  │ STEP D: Run Code Reviewer     │      │
│  │                               │      │
│  │ "Is it clean?"                │      │
│  │                               │      │
│  │ Give Claude (fresh session):  │      │
│  │ • code-reviewer.md prompt     │      │
│  │ • Code diff / new files       │      │
│  │ • coding-standards.md         │      │
│  │ • architecture.md             │      │
│  │                               │      │
│  │ Checks: TypeScript, naming,   │      │
│  │ error handling, test quality,  │      │
│  │ AI-specific standards          │      │
│  └────────────┬──────────────────┘      │
│               │                         │
│          ┌────▼────┐                    │
│          │ VERDICT │                    │
│          └────┬────┘                    │
│          ┌────┴────┐                    │
│          │         │                    │
│       ✅ PASS   ❌ FAIL                 │
│          │         │                    │
│          │         ▼                    │
│          │   ┌──────────────┐           │
│          │   │ Feed issues  │           │
│          │   │ to Builder   │           │
│          │   │ Loop +1      │           │
│          │   │ (max 2)      │           │
│          │   └──────────────┘           │
│          │                              │
│          ▼                              │
│  ┌──────────┐                           │
│  │ Commit ✓ │                           │
│  │ Update   │                           │
│  │ sprint.md│                           │
│  │ → Done   │                           │
│  └──────────┘                           │
│                                         │
│  ── Repeat for next task ──             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│        END OF DAY (15 min)              │
│                                         │
│  1. Update sprint.md task statuses      │
│  2. Note blockers                       │
│  3. Run Scrum Master (Daily Mode):      │
│     • Paste tasks worked on today       │
│     • Paste tasks completed             │
│     • Paste blockers                    │
│     • Approximate hours worked/left     │
│  4. Read standup report                 │
│  5. Act on recommendations:             │
│     • Descope?                          │
│     • Reprioritize?                     │
│     • Rewrite a task spec?             │
│  6. Quick retro note in retro.md        │
└─────────────────────────────────────────┘
```

### Build Cycle Rules

1. **One task at a time.** Don't parallel-track. Finish or explicitly block before moving on.
2. **Fresh Claude session for each review agent.** QA gets a fresh session. Code Reviewer gets a fresh session. No context contamination.
3. **QA runs before Code Reviewer.** No point checking code quality if the feature doesn't work.
4. **Loop limits are hard limits.** QA: max 3 loops. Code Reviewer: max 2 loops. Total max 5 per task. If exceeded, the problem is in the task spec — rewrite it.
5. **Commit after every passing task.** Small, frequent commits. Don't batch.
6. **Update sprint.md immediately** when a task status changes. This is your live dashboard.
7. **Never skip the Scrum Master daily.** It's 5 minutes and it's how you catch problems early.

### What to Feed Each Agent

**Builder (Claude Code):**

```
Context (attach or paste):
├─ architecture.md (relevant sections)
├─ coding-standards.md
└─ The specific task block from sprint.md

Prompt pattern:
"Implement TASK-XXX: [title]

Description: [from sprint.md]

Acceptance criteria:
- [criterion 1]
- [criterion 2]
- [criterion 3]

Builder notes: [from sprint.md]

Follow the coding standards in the attached file.
Files should go in: [paths from architecture.md]"
```

**QA Agent (fresh Claude session):**

```
Context (attach or paste):
├─ qa-agent.md prompt template
└─ definition-of-done.md

Then paste:
1. The task spec + acceptance criteria (from sprint.md)
2. Output of npm run check
3. The code diff or new files
```

**Code Reviewer (fresh Claude session):**

```
Context (attach or paste):
├─ code-reviewer.md prompt template
├─ coding-standards.md
└─ architecture.md

Then paste:
1. The code diff or new/modified files
```

**Scrum Master — Daily Mode (fresh Claude session):**

```
Context (attach or paste):
├─ scrum-master.md prompt template (Mode 1)
├─ sprint.md (current state)
├─ definition-of-done.md
└─ retro.md

Then fill in:
1. Tasks worked on today
2. Tasks completed today
3. Blockers
4. Hours worked / remaining
5. Anything unusual
```

---

## Phase 4: Sprint Close (Every 2-3 Days)

**Goal:** Evaluate the sprint holistically, capture learnings, prepare for next.

**Time:** 45-60 minutes.

**Agent:** Scrum Master (Sprint Close Mode) + you

### Steps

```
4.1  Run Scrum Master in Sprint Close Mode
     └─ Use scrum-master.md prompt (Mode 2)
     └─ Attach:
        ├─ sprint.md (with final statuses)
        ├─ architecture.md
        ├─ decisions.md
        └─ retro.md
     └─ Paste summary of all files created/modified this sprint
     └─ Paste the sprint goal
     └─ Scrum Master produces:
        ├─ Integration coherence check
        ├─ Architectural alignment check
        ├─ Technical debt assessment
        ├─ Velocity summary
        ├─ Risk forecast for next sprint
        └─ Specific document update recommendations

4.2  Manual smoke test
     └─ Launch the app
     └─ Walk through the sprint goal end-to-end
     └─ Does it actually work as a user would experience it?
     └─ Note any issues

4.3  Fill out Sprint Summary in sprint.md
     └─ Tasks completed vs planned
     └─ Velocity (complexity points completed)
     └─ Key blockers
     └─ Notes for next sprint

4.4  Sprint Retrospective
     └─ Fill out retro.md for this sprint:
        ├─ What went well
        ├─ What slowed you down
        ├─ AI-specific observations
        ├─ Prompt adjustments needed
        └─ Process adjustments needed

4.5  Update living documents
     └─ Follow Scrum Master's document update recommendations
     └─ architecture.md — if structure changed
     └─ decisions.md — if you made new technical choices
     └─ coding-standards.md — if new patterns should be codified
     └─ backlog.md — move completed items, reprioritize if needed

4.6  Archive sprint
     └─ Rename sprint.md → sprint-1.md (or move to /workflow/archive/)
     └─ Create fresh sprint.md for next sprint
```

### Outputs

```
  ✅ sprint.md                (summary filled, archived)
  ✅ retro.md                 (new entry added)
  ✅ architecture.md          (updated if changed)
  ✅ decisions.md             (new entries if applicable)
  ✅ coding-standards.md      (new patterns if applicable)
  ✅ backlog.md               (completed items moved, reprioritized)
```

---

## Phase 5: Next Sprint (Repeat Phase 2)

Loop back to Phase 2 with fresh context. The Product Owner now has:

- Updated backlog
- Sprint velocity data (how much you actually complete)
- Retro notes (what to avoid)
- Updated architecture (current state of the system)
- Scrum Master's risk forecast (what to watch for)

Each sprint gets tighter because your context files improve.

---

## The 4-Week Timeline

```
Week 1
├─ Day 1-2:   Phase 1 (Foundation) + Phase 2 (Sprint 1 Planning)
├─ Day 3-5:   Phase 3 (Build Sprint 1: project setup, editor, auth)
└─ Day 5:     Phase 4 (Sprint 1 Close)

Week 2
├─ Day 1:     Phase 2 (Sprint 2 Planning)
├─ Day 1-4:   Phase 3 (Build Sprint 2: note persistence, AI autocomplete)
└─ Day 4-5:   Phase 4 (Sprint 2 Close)

Week 3
├─ Day 1:     Phase 2 (Sprint 3 Planning)
├─ Day 1-4:   Phase 3 (Build Sprint 3: definition lookup, study mode)
└─ Day 4-5:   Phase 4 (Sprint 3 Close)

Week 4
├─ Day 1:     Phase 2 (Sprint 4 Planning)
├─ Day 1-3:   Phase 3 (Build Sprint 4: polish, bug fixes, integration)
├─ Day 3-4:   Full end-to-end testing
└─ Day 5:     MVP ship 🚀
```

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────┐
│                  DAILY CHEAT SHEET                      │
│                                                         │
│  Morning:                                               │
│    Review sprint.md → pick task                         │
│                                                         │
│  Per task:                                              │
│    Builder → npm run check → QA Agent → Code Reviewer   │
│    → commit                                             │
│                                                         │
│  End of day:                                            │
│    Update statuses → Scrum Master (Daily) → retro note  │
│                                                         │
│  Sprint start:                                          │
│    Product Owner → you approve → sprint.md              │
│                                                         │
│  Sprint end:                                            │
│    Scrum Master (Sprint Close) → smoke test → retro     │
│    → update docs → archive                              │
│                                                         │
│  AGENTS + PROMPTS:                                      │
│  Product Owner  = Claude + product-owner.md + docs      │
│  Builder        = Claude Code + task spec + standards   │
│  QA Agent       = Claude + qa-agent.md + task spec      │
│  Code Reviewer  = Claude + code-reviewer.md + diff      │
│  Scrum Master   = Claude + scrum-master.md + sprint.md  │
│                                                         │
│  RULES:                                                 │
│  ✦ One task at a time                                   │
│  ✦ npm run check before every QA review                 │
│  ✦ Fresh session for QA, Code Reviewer, Scrum Master    │
│  ✦ QA max 3 loops, Code Reviewer max 2 loops            │
│  ✦ Commit after every pass                              │
│  ✦ Update sprint.md immediately                         │
│  ✦ Never skip the daily Scrum Master                    │
└────────────────────────────────────────────────────────┘
```

---

## When to Update Each Document

| Document              | Update When                                    |
| --------------------- | ---------------------------------------------- |
| product-brief.md      | MVP scope changes (rare)                       |
| architecture.md       | New component, dependency, or data model added |
| coding-standards.md   | New convention established via retro           |
| definition-of-done.md | Quality bar changes (rare)                     |
| decisions.md          | Any significant technical choice               |
| backlog.md            | Sprint planning + sprint close                 |
| sprint.md             | Daily (task statuses) + sprint close (summary) |
| retro.md              | Daily (notes) + sprint close (full entry)      |

---

## File Map

```
/docs
  product-brief.md
  architecture.md
  coding-standards.md
  definition-of-done.md
  decisions.md

/workflow
  backlog.md
  sprint.md
  retro.md
  agent-roster.md
  WORKFLOW.md              ← you are here
  /prompts
    product-owner.md
    scrum-master.md
    qa-agent.md
    code-reviewer.md
```
