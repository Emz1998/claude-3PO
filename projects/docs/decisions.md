# Technical Decisions

**Project:** TestApp (E2E Test)
**Version:** v1.0
**Date:** 2026-04-16

---

## Decision 1: Backend Language & Framework

**Decision:** Python/FastAPI
**Rationale:** Strong AI/ML ecosystem, async support, team familiarity.
**Trade-offs:** GIL limits true parallelism, but async I/O mitigates this.

---

## Decision 2: Frontend Framework

**Decision:** React + Next.js
**Rationale:** SSR support, strong ecosystem, reusable component libraries.
**Trade-offs:** Larger bundle size, but acceptable for productivity tool.

---

## Decision 3: Database

**Decision:** PostgreSQL
**Rationale:** Relational data model fits project management entities. Strong ACID guarantees.
**Trade-offs:** More complex to scale horizontally than NoSQL.

---

## Decision 4: Authentication

**Decision:** JWT + OAuth2 (Google, GitHub)
**Rationale:** Reduces friction, users already have accounts, standard pattern.
**Trade-offs:** JWT refresh management adds complexity.

---

## Decision 5: Architecture

**Decision:** Monolith (modular)
**Rationale:** Faster to build for MVP, easier to debug.
**Trade-offs:** Harder to scale individual services later.

---

## Decision 6: Cloud Provider

**Decision:** AWS
**Rationale:** Broadest service ecosystem, team familiarity, easy to scale.
**Trade-offs:** Higher cost at low scale vs. simpler providers.

---

## Decision 7: API Strategy

**Decision:** REST
**Rationale:** Simple, well-understood, adequate for CRUD operations.
**Trade-offs:** No real-time subscriptions (add WebSockets separately if needed).

---

## Decision 8: CI/CD

**Decision:** GitHub Actions
**Rationale:** Native GitHub integration, zero additional cost for public repos.
**Trade-offs:** Limited parallelism on free tier.

---

## Decision 9: Third-Party Integrations

**Decision:** Slack, GitHub
**Rationale:** Where developers already work — meet users where they are.
**Trade-offs:** Maintenance burden of 2 integrations for MVP.

---

## Decision 10: Non-Negotiable Constraints

- Response time < 2 seconds for all primary actions
- 99.9% uptime SLA
- All user data encrypted at rest and in transit
- GDPR compliance required (EU users)
