# Technical Decisions — NEXLY RN

> **Purpose:** Record key technical choices so AI agents and future-you understand WHY things are built this way. Add a new entry whenever you make a meaningful architectural or tooling decision.

---

## Template

### DECISION-XXX: [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted / Superseded / Revisiting
**Context:** What situation prompted this decision?
**Decision:** What did you choose?
**Alternatives considered:** What else did you evaluate?
**Rationale:** Why this choice over the alternatives?
**Consequences:** What trade-offs come with this?

---

## Decisions

### DECISION-001: Desktop-first with Tauri

**Date:** [fill in]
**Status:** Accepted
**Context:** Need to ship a desktop app. Options were Electron, Tauri, or web-only.
**Decision:** Tauri v2 for desktop shell.
**Alternatives:** Electron (heavy, large bundle), web-only (loses desktop integration)
**Rationale:** Smaller bundle, Rust backend, better performance. Nursing students often work on older laptops.
**Consequences:** Some web APIs may not work. Need to test browser features in Tauri webview.

### DECISION-002: Firebase for backend

**Date:** [fill in]
**Status:** Accepted
**Context:** Need auth + data storage with minimal backend code as a solo dev.
**Decision:** Firebase (Auth + Firestore).
**Alternatives:** Supabase (Postgres-based), custom backend
**Rationale:** Fastest to implement, good free tier, familiar. Firestore's document model fits notes well.
**Consequences:** Vendor lock-in. Migration would require effort later. No SQL queries.

### DECISION-003: [Next decision]

<!-- Add as you go -->
