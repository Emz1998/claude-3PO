# Definition of Done

**Project:** Avaris AI
**Version:** v1.0
**Last Updated:** 2026-02-10

---

## Task Level

_Checked by: QA Agent, Code Reviewer, then You. A task is Done when ALL of the following pass._

**Automated Gate (`npm run check` for web, `pytest && mypy` for pipeline)**

- Type checker passes with zero errors
- Linter reports no new warnings or errors
- Test suite passes (all existing + new tests)

**QA Agent Pass**

- Every acceptance criterion from the sprint/task verified as met
- New tests cover the task's critical logic paths
- Firebase/Firestore interactions verified (correct collection, correct document shape)
- Pipeline changes: predictions output matches expected schema
- Dashboard changes: data renders correctly with real and empty data states

**Code Reviewer Pass**

- Naming conventions follow `coding-standards.md`
- Error handling present on all external calls (Firebase, NBA API, Vercel webhooks)
- Files placed in correct directories per `architecture.md`
- No `any` types in TypeScript without justifying comment
- Python functions have type hints on public signatures
- Secrets/config use environment variables, never hardcoded
- ML predictions validated against expected schema before Firestore write

**Final**

- Committed with descriptive conventional commit message
- Sprint/task status updated to Done

---

## Sprint Level

_Checked by: Scrum Master (sprint close), then You. A sprint is Done when ALL pass._

**Scrum Master Sprint Close**

- All completed tasks meet task-level DoD
- Integration coherence: completed features work together without conflicts
- Architectural alignment: codebase matches `architecture.md`
- No critical technical debt introduced (tracked shortcuts are acceptable)

**Your Manual Check**

- Smoke test: visit the live site, verify daily picks display, dashboard loads, navigation works
- No broken user flows from previously completed sprints (regression check)
- Sprint summary documented (velocity, blockers, notes)
- Living docs updated per Scrum Master recommendations:
  - `architecture.md` if structure changed
  - `decisions.md` if new technical choices made
  - `coding-standards.md` if new patterns established

---

## Release Level

_Checked by: You. The product is ready to ship when ALL pass._

**Quality**

- All sprint-level criteria met for final sprint
- Full check commands passing across entire codebase (web + pipeline)
- All MVP features functional end-to-end:
  - XGBoost prediction model generating daily predictions
  - Auto-generated SEO blog posts publishing correctly
  - Public performance dashboard displaying accurate data
  - Automated pipeline running daily without manual intervention
  - Google AdSense displaying ads on prediction pages
- Data persistence verified: predictions write to Firestore and display on site correctly

**Stability**

- Site loads reliably on target browsers (Chrome, Firefox, Safari, Edge)
- Blog posts load in < 2 seconds (SSG from CDN)
- Dashboard loads in < 3 seconds (ISR with Firestore fetch)
- Graceful degradation when NBA API is slow or unavailable (cached data served)
- No console errors during normal usage flow

**Ship Readiness**

- `architecture.md` reflects final state of the system
- `decisions.md` is current (no unlogged decisions)
- README.md with setup, development, and deployment instructions
- Vercel production deployment verified and working
- GitHub Actions pipeline tested and running on schedule

---

## What Done Does NOT Require at MVP

- Performance benchmarking or load testing
- Security audit (no user data collected)
- Accessibility audit (target post-MVP)
- Cross-platform mobile testing (desktop-first)
- CI/CD pipeline beyond GitHub Actions + Vercel auto-deploy
- High test coverage threshold (cover critical paths, not everything)
- Monitoring dashboards (alerting on failures is sufficient)

---

## Document History

- **v1.0** - 2026-02-10 - emhar - Initial DoD from coding-standards.md and architecture.md
