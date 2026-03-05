# Development Architecture

**Project:** Avaris
**Version:** v1.0
**Date:** 2026-02-10
**Author:** emhar
**Status:** Draft

---

## Project Overview

**Purpose** - Avaris is an ML-powered website that delivers daily NBA game predictions as SEO-optimized blog posts with a live, public performance dashboard. It solves the transparency problem in NBA prediction services by making every prediction verifiable.

**In Scope** - XGBoost prediction model (moneyline), auto-generated SEO blog posts, public performance dashboard, automated daily pipeline, Google AdSense integration.

**Out of Scope** - Subscription/payment system, spread/totals predictions, desktop prediction bot, API access, mobile apps, multi-sport.

**Future Considerations** - Premium subscription tier, additional bet types, email newsletter system, sportsbook affiliate integrations.

**Key Terms**

- **Moneyline** - A bet on which team wins outright
- **XGBoost** - Gradient boosting ML algorithm for tabular data predictions
- **ISR** - Incremental Static Regeneration, Next.js feature for updating static pages
- **nba_api** - Python library wrapping stats.nba.com endpoints

---

## Architectural Decisions

**Architecture Style** - Hybrid: Static-first web application (Next.js SSG/ISR) + scheduled Python ML pipeline. Two independent subsystems connected through shared data store (Firestore) and content generation (GitHub repo).

**Rationale** - Solo developer needs minimal ops overhead. Static pages are fast, cheap, and SEO-friendly. Python pipeline runs on a schedule, not in response to user requests. Decoupling web and ML means each can be developed, tested, and deployed independently.

**Key ADRs** - See `decisions.md` for full records.

- **ADR-001** - Next.js 15 for web framework (SSG/ISR for SEO, Vercel integration)
- **ADR-002** - XGBoost for prediction model (gold standard for tabular data, fast retraining)
- **ADR-003** - Vercel for hosting (free tier, purpose-built for Next.js)
- **ADR-004** - Firebase Firestore for data storage (document model fits predictions, free tier)
- **ADR-005** - GitHub Actions for daily automation pipeline (free, cron scheduling)
- **ADR-006** - Tailwind v4 for styling (fast iteration, no runtime overhead)
- **ADR-007** - Python nba_api for data ingestion (free NBA data access)

---

## System Context

- **Primary Users** - Casual and serious NBA bettors, 5k-50k monthly visitors (MVP target)
- **External Systems** - NBA Stats API (data source), Firebase (data store), Google AdSense (ads), Google Analytics (analytics)
- **Downstream Consumers** - None at MVP
- **System Boundary** - Avaris owns the prediction model, blog content, and dashboard. It does not own NBA data, ad serving, or analytics.

**Architecture Overview**

```
[GitHub Actions Cron - Daily]
    |
    v
[Python ML Pipeline]
    |-- Fetch NBA data (nba_api -> stats.nba.com)
    |-- Retrain XGBoost model
    |-- Generate predictions
    |-- Write results to Firestore
    |-- Generate blog post content
    |-- Trigger Vercel rebuild (webhook)
    v
[Next.js on Vercel]
    |-- SSG blog posts (daily predictions)
    |-- ISR dashboard (performance data from Firestore)
    |-- Static pages (about, methodology)
    |-- Google AdSense (display ads)
    v
[User Browser]
```

---

## System Components

**Project Structure**

```
/src                        - Next.js web application
  /app                      - App Router pages and layouts
    /blog                   - Daily prediction blog posts
    /dashboard              - Performance dashboard
  /components               - React components
    /blog                   - Blog-specific components
    /dashboard              - Dashboard charts and widgets
    /layout                 - Header, footer, navigation
  /lib                      - Shared utilities and Firebase client
  /types                    - TypeScript type definitions
/pipeline                   - Python ML pipeline
  /data                     - Data ingestion and feature engineering
  /model                    - XGBoost training and prediction
  /publish                  - Blog content generation and Firestore writes
  /tests                    - Python pipeline tests (pytest)
/public                     - Static assets (images, favicon)
```

**Key rules:**

- `/src/app` routes are thin wrappers that call into `/src/lib` or `/src/components`
- Business logic lives in `/src/lib`, not in route handlers or components
- Python pipeline is fully independent of the Next.js app; communicates only through Firestore and generated content
- Components import from `/src/lib` and `/src/types`, never directly from Firebase SDK

**Frontend Layer**

- **Framework** - Next.js 15 (React 19), App Router
- **Language** - TypeScript (strict mode)
- **State Management** - React Server Components for data fetching, minimal client state
- **UI Library** - Tailwind CSS v4
- **Rendering Strategy** - SSG for blog posts (built at deploy time + ISR), SSR/ISR for dashboard (revalidates periodically)
- **Hosting** - Vercel (free Hobby tier)

**API Layer** - No custom API at MVP. Next.js Server Components fetch directly from Firestore. Python pipeline writes directly to Firestore.

**Database Layer**

- **Database** - Firebase Firestore (NoSQL document database)
- **Hosting** - Google Cloud (managed, free Spark plan)
- **Collections:**
  - `predictions` - Daily game predictions (gameId, date, homeTeam, awayTeam, predictedWinner, probability, actualResult)
  - `performance` - Aggregated performance metrics (date, totalPicks, wins, losses, winRate, roi)
  - `blog_metadata` - Blog post metadata for SSG (slug, date, title, teams, status)

**Caching Strategy**

- **Blog posts** - SSG at build time, ISR revalidation every 1 hour during game days
- **Dashboard** - ISR with 15-minute revalidation (balances freshness with free tier limits)
- **Static assets** - CDN with immutable hashes (Vercel handles this automatically)
- **Default posture** - Static by default; only dashboard data is dynamic

---

## Data Flow

**Primary Request Flow (User views daily picks)**

1. User searches Google, clicks Avaris blog post link
2. Vercel CDN serves pre-rendered SSG page (no server round-trip)
3. If page is stale, ISR revalidates in background for next visitor
4. Blog post displays predictions with probabilities from build-time data

**Daily Prediction Pipeline (Automated)**

1. GitHub Actions cron triggers at configured time (e.g., 10:00 AM ET)
2. Python script fetches latest NBA data via `nba_api`
3. XGBoost model retrains on updated dataset
4. Predictions generated for today's scheduled games
5. Results written to Firestore `predictions` collection
6. Blog post markdown generated from prediction data
7. Vercel deploy hook triggered to rebuild static pages
8. Dashboard ISR picks up new performance data on next revalidation

**Results Update Pipeline (Automated)**

1. GitHub Actions cron triggers after games complete (e.g., 1:00 AM ET)
2. Python script fetches game results via `nba_api`
3. Prediction documents updated in Firestore with actual results
4. Performance aggregation recalculated and written to `performance` collection

**Third-Party Integrations**

- **NBA Stats API (stats.nba.com)** - Data source for all NBA stats. Protocol: HTTP via nba_api Python library. Fallback: cached data serves stale predictions with warning.
- **Firebase Firestore** - Data store. Protocol: Firebase Admin SDK (Python), Firebase JS SDK (Next.js). Fallback: SSG pages still serve from last successful build.
- **Google AdSense** - Ad serving. Protocol: client-side script tag. Fallback: ad slot is empty, no user impact.
- **Vercel** - Hosting and CDN. Fallback: none (single point of failure for serving).

---

## Security Architecture

**Authorization Model** - No auth at MVP. All content is public. No user accounts, no user data. Firestore rules set to read-only for client access, write access restricted to service account (Python pipeline only).

**API and Network Protection**

- **CORS** - Default Next.js CORS (same-origin)
- **CSP** - Configured to allow AdSense scripts and analytics
- **Input validation** - No user input at MVP (read-only site)
- **Rate limiting** - Not needed at MVP (no API, no user input)

**Data Protection**

- **Encryption in transit** - TLS via Vercel (automatic HTTPS)
- **Encryption at rest** - Google Cloud default encryption for Firestore
- **Secrets** - Firebase service account key and deploy hook URL stored in GitHub Secrets
- **Sensitive keys** - Only accessible in GitHub Actions environment, never in client bundle

---

## Testing Strategy

- **Type checking** - `tsc --noEmit` - Full codebase - Every commit (CI)
- **Linting** - ESLint + Prettier - Full codebase - Every commit (CI)
- **Unit tests (web)** - Vitest - Components, lib utilities, type transformations - Every commit (CI)
- **Unit tests (pipeline)** - pytest - Data processing, feature engineering, model predictions - Every commit (CI)
- **Integration tests** - Vitest - Firestore data fetching, blog post generation - Every PR
- **E2E tests** - Playwright - Blog post renders, dashboard loads, navigation works - Pre-deploy

_Focus E2E coverage on: (1) daily picks page loads with predictions, (2) dashboard displays performance data, (3) blog post SEO metadata is correct._

---

## Observability

- **Error tracking** - Vercel built-in error logging (MVP), Sentry if needed later
- **Logging** - GitHub Actions logs for pipeline runs, Vercel function logs for server errors
- **Uptime monitoring** - Free tier uptime monitor (e.g., UptimeRobot) checking homepage and dashboard
- **Alerting** - GitHub Actions failure notifications via email, UptimeRobot alerts for downtime

_At MVP, the critical alert is: "Did today's prediction pipeline run successfully?" Monitor GitHub Actions workflow status daily._

---

## DevOps and Deployment

**Source Control** - GitHub, trunk-based development (main branch), PRs required for web changes, pipeline changes can go direct to main with CI passing.

**Deployment**

- **Web app** - Vercel auto-deploys on push to main. Preview deployments on PRs.
- **Python pipeline** - Runs in GitHub Actions. No separate deployment; code runs from repo.
- **Rollback** - Vercel instant rollback to previous deployment. Pipeline rollback via git revert.
- **Database migrations** - No schema migrations (Firestore is schemaless). Collection structure changes documented in this file.

**Environments**

- **Local** - Next.js dev server + Firebase emulator + Python venv
- **Preview** - Vercel preview deployments (per-PR)
- **Production** - Vercel production + Firebase Spark plan + GitHub Actions cron

---

## Cost and Operations

**Monthly Cost Estimate (MVP)**

- **Hosting (Vercel)** - Free Hobby tier - $0
- **Database (Firebase Firestore)** - Free Spark plan (1GB storage, 50k reads/day) - $0
- **CI/CD (GitHub Actions)** - Free tier (2,000 min/month) - $0
- **Domain** - ~$12/year - ~$1/month
- **Analytics (Google Analytics)** - Free - $0
- **Ads (AdSense)** - Revenue, not cost - $0
- **Total** - ~$1/month

**Scaling Triggers**

- **Vercel bandwidth > 100GB/month** - ~50k+ monthly visitors - Upgrade to Pro ($20/month)
- **Firestore reads > 50k/day** - High dashboard traffic - Upgrade to Blaze (pay-as-you-go)
- **GitHub Actions > 2,000 min/month** - Only if pipeline becomes complex - Upgrade or optimize

---

## Risks, Assumptions, and Constraints

**Assumptions**

- Traffic stays below Vercel/Firebase free tier limits for first 3 months
- Solo developer for at least 6 months
- NBA Stats API remains free and rate limits are manageable with caching

**Constraints**

- Budget capped at ~$20/month maximum for MVP phase (business constraint)
- Must use approved tech stack per constitution (React 19, Next.js, Tailwind v4, TypeScript, Firebase)
- XGBoost model must retrain within GitHub Actions 6-hour job limit

**Risks**

- **NBA Stats API becomes unavailable** - Likelihood: Low, Impact: High - Mitigation: aggressive caching, fallback to cached data
- **Vercel free tier insufficient for traffic** - Likelihood: Medium, Impact: Medium - Mitigation: cost triggers at 80% of limits
- **Pipeline failure silently skips a day** - Likelihood: Medium, Impact: High - Mitigation: alerting on workflow failure, health check for "latest prediction is today"
- **Firestore query patterns don't support dashboard needs** - Likelihood: Low, Impact: Medium - Mitigation: denormalize performance data into pre-aggregated documents

---

## Document History

- **v1.0** - 2026-02-10 - emhar - Initial architecture from product-brief and decisions
