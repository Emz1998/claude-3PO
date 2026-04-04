# Definition of Done (DoD)

**Project:** `[Project Name]`
**Version:** `[v1.0]`
**Last Updated:** `[YYYY-MM-DD]`

---

## Task Level

> **Checked by:** QA Agent → Code Reviewer → You
> A task is Done when ALL of the following pass.

### Automated Gate (`[your check command, e.g. npm run check]`)

- [ ] Type checker — zero errors
- [ ] Linter — no new warnings or errors
- [ ] Test suite — all tests passing

### QA Agent Pass

- [ ] Every acceptance criterion from sprint.md verified as met
- [ ] New tests cover the task's critical logic paths
- [ ] `[Project-specific QA checks, e.g.:]`
  - [ ] `[AI integration: response validation and timeout handling confirmed]`
  - [ ] `[API changes: request/response contracts verified]`
  - [ ] `[UI changes: renders correctly in target environment]`

### Code Reviewer Pass

- [ ] Naming conventions follow coding-standards.md
- [ ] Error handling present on all `[external service calls, e.g. API, database, third-party]`
- [ ] Files placed in correct directories per architecture.md
- [ ] `[Language-specific checks, e.g.:]`
  - [ ] `[TypeScript: no 'any' types without justifying comment]`
  - [ ] `[Python: type hints on all public functions]`
- [ ] `[Project-specific standards, e.g.:]`
  - [ ] `[AI prompts stored in designated directory, not hardcoded]`
  - [ ] `[Environment variables used for secrets/config, not hardcoded]`

### Final

- [ ] Committed with descriptive message
- [ ] sprint.md status updated to Done

---

## Sprint Level

> **Checked by:** Scrum Master (Sprint Close Mode) → You
> A sprint is Done when ALL of the following pass.

### Scrum Master Sprint Close

- [ ] All completed tasks meet task-level DoD
- [ ] Integration coherence: completed features work together without conflicts
- [ ] Architectural alignment: codebase matches architecture.md
- [ ] No critical technical debt introduced (tracked shortcuts are acceptable)

### Your Manual Check

- [ ] Smoke test: launch app, walk through sprint goal end-to-end
- [ ] No broken user flows from previously completed sprints (regression check)
- [ ] Sprint summary filled in sprint.md (velocity, blockers, notes)
- [ ] retro.md updated with sprint observations
- [ ] Living docs updated per Scrum Master recommendations:
  - [ ] architecture.md (if structure changed)
  - [ ] decisions.md (if new technical choices made)
  - [ ] coding-standards.md (if new patterns established)
  - [ ] backlog.md (completed items moved, reprioritized)

---

## Release Level

> **Checked by:** You
> The product is ready to ship when ALL of the following pass.

### Quality

- [ ] All sprint-level criteria met for final sprint
- [ ] Full `[check command]` passing across entire codebase
- [ ] All MVP features functional end-to-end:
  - [ ] `[Feature 1]`
  - [ ] `[Feature 2]`
  - [ ] `[Feature 3]`
  - [ ] `[Feature 4]`
- [ ] `[Auth/core flow works, e.g. sign up, log in, primary user journey]`
- [ ] `[Data persistence verified, e.g. saves and loads correctly]`

### Stability

- [ ] App launches reliably in target environment (`[e.g. browser, desktop shell, mobile]`)
- [ ] `[Performance-sensitive features]` respond within acceptable time (~`[X]` seconds)
- [ ] Graceful degradation when `[external dependency]` is slow or unavailable
- [ ] No console errors during normal usage flow

### Ship Readiness

- [ ] architecture.md reflects final state of the system
- [ ] decisions.md is current (no unlogged decisions)
- [ ] README.md with setup/run instructions
- [ ] `[Build/deploy output verified, e.g. distributable binary, deployable bundle]`

---

## What Done Does NOT Require

> Customize this per project. List things that are explicitly out of scope
> for your current milestone to prevent scope creep at the quality gate.

- [ ] `[e.g. Performance benchmarking or load testing]`
- [ ] `[e.g. Security audit]`
- [ ] `[e.g. Accessibility audit]`
- [ ] `[e.g. Cross-platform testing]`
- [ ] `[e.g. CI/CD pipeline]`
- [ ] `[e.g. Monitoring or alerting]`
- [ ] `[e.g. High test coverage threshold — cover critical paths, not everything]`

---

## How Each Agent Uses This Document

| Agent         | Uses DoD For                                           |
| ------------- | ------------------------------------------------------ |
| Product Owner | Writing testable acceptance criteria that align to DoD |
| Builder       | Knowing what quality bar to meet while coding          |
| QA Agent      | Checking task completion against task-level criteria   |
| Code Reviewer | Checking code quality against task-level standards     |
| Scrum Master  | Checking sprint health against sprint-level criteria   |
