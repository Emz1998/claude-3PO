# Technical Decisions

**Project:** Avaris AI
**Version:** v1.0
**Last Updated:** 2026-02-10

_Record key technical choices so future-you understands WHY things are built this way. Add a new entry whenever you make a meaningful architectural or tooling decision._

---

## DECISION-001: Next.js for web framework

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need a web framework for an SEO-optimized blog with daily auto-generated prediction content and a performance dashboard.
**Decision:** Next.js 15 (App Router) with React 19.
**Alternatives considered:** Astro (good for static content but weaker for dynamic dashboard), Gatsby (declining ecosystem), plain React SPA (no SSR/SSG, poor SEO).
**Rationale:** Next.js provides SSG for blog posts (critical for SEO), ISR for dashboard updates, and excellent Vercel integration. React 19 ecosystem has the largest library support. App Router aligns with modern React patterns.
**Consequences:** Tied to Vercel for optimal deployment. App Router has some learning curve. Server Components add complexity.

---

## DECISION-002: XGBoost for prediction model

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need an ML model for daily NBA game predictions (moneyline) that a solo developer can build, train, and maintain.
**Decision:** XGBoost (Python) with nightly retraining.
**Alternatives considered:** Neural networks (complex, slow to train, overkill for tabular data), logistic regression (too simple, limited feature interactions), LightGBM (comparable but XGBoost has better documentation and community).
**Rationale:** XGBoost is the gold standard for tabular data. Fast training allows nightly retraining. Well-documented, battle-tested, and can run on minimal compute. Python ecosystem (pandas, nba_api) makes data pipeline straightforward.
**Consequences:** Python required for ML pipeline alongside TypeScript for web. Two-language codebase adds some complexity but is industry-standard for ML + web.

---

## DECISION-003: Vercel for hosting

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need hosting for a Next.js site with SSG pages, ISR, and edge CDN delivery. Budget is near-zero for MVP.
**Decision:** Vercel (free Hobby tier).
**Alternatives considered:** Netlify (good but weaker Next.js integration), AWS Amplify (more complex setup), self-hosted (unnecessary ops burden).
**Rationale:** Vercel is purpose-built for Next.js. Free tier covers MVP traffic easily. Automatic CDN, preview deployments, and zero-config deployment from GitHub. ISR support is native.
**Consequences:** Vendor lock-in to Vercel-specific features (ISR, edge functions). Free tier has bandwidth limits (100GB/month) that may require upgrade if traffic exceeds ~50k monthly visitors.

---

## DECISION-004: Firebase for backend services

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need data storage for predictions, game results, and performance metrics. Auth needed for future premium tier but not MVP.
**Decision:** Firebase (Firestore for data, Auth reserved for Phase 3).
**Alternatives considered:** Supabase (Postgres-based, more flexible queries), custom backend (unnecessary complexity for MVP), flat files/JSON (not scalable enough for dashboard queries).
**Rationale:** Firestore's document model fits predictions well (each prediction is a self-contained document). Free Spark plan covers MVP usage. Familiar to solo dev. Auth can be added later without migration.
**Consequences:** No SQL queries (must structure data for Firestore's query model). Vendor lock-in to Google ecosystem. Document model requires denormalization for dashboard aggregations.

---

## DECISION-005: GitHub Actions for automation pipeline

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need automated daily pipeline: fetch NBA data, retrain model, generate predictions, publish blog posts.
**Decision:** GitHub Actions with scheduled cron workflows.
**Alternatives considered:** AWS Lambda + CloudWatch (more complex, costs money), self-hosted cron (unreliable without monitoring), manual process (defeats the purpose).
**Rationale:** Free for public repos (2,000 minutes/month for private). Cron scheduling built-in. Direct access to repo for pushing generated content. Already using GitHub for source control.
**Consequences:** 6-hour maximum job runtime. Dependent on GitHub's uptime for daily predictions. Secrets management through GitHub Secrets.

---

## DECISION-006: Tailwind CSS v4 for styling

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need a styling approach for the prediction blog and dashboard that supports rapid development.
**Decision:** Tailwind CSS v4.
**Alternatives considered:** CSS Modules (more boilerplate), styled-components (runtime overhead), plain CSS (slower iteration).
**Rationale:** Utility-first approach speeds up development. v4 has improved performance with Oxide engine. No runtime CSS overhead. Consistent with constitution's approved tech stack.
**Consequences:** HTML can become verbose with many utility classes. Requires learning Tailwind conventions.

---

## DECISION-007: Python + nba_api for data ingestion

**Date:** 2026-02-10
**Status:** Accepted
**Context:** Need reliable access to NBA game data, player stats, team stats, and game schedules for model features.
**Decision:** Python `nba_api` library as primary data source, with aggressive caching.
**Alternatives considered:** Direct stats.nba.com scraping (fragile, rate-limited), paid data providers (unnecessary cost for MVP), Basketball Reference scraping (slower, less structured).
**Rationale:** `nba_api` is the most popular Python wrapper for stats.nba.com with active maintenance. Free access to comprehensive NBA data. Community-supported with good documentation.
**Consequences:** Subject to NBA Stats API rate limits and potential breaking changes. Must cache data aggressively. Need fallback strategy if API becomes unavailable.

---

## Document History

- **v1.0** - 2026-02-10 - emhar - Initial decisions from product-brief and architecture planning
