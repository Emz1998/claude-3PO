# 📐 Development Architecture Document (Lean MVP)

---

**Project Name:** `<PROJECT_NAME>`
**Version:** `<VERSION_NUMBER>`
**Date:** `<DATE>`
**Author(s):** `<AUTHOR_NAME(S)>`
**Status:** Draft / In Review / Approved
**Last Reviewed:** `<DATE>`
**Approved By:** `<APPROVER_NAME>`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architectural Decisions](#2-architectural-decisions)
3. [System Context & High-Level Architecture](#3-system-context--high-level-architecture)
4. [System Components](#4-system-components)
5. [Data Flow & Integration Patterns](#5-data-flow--integration-patterns)
6. [Security Architecture](#6-security-architecture)
7. [Testing Strategy](#7-testing-strategy)
8. [Observability](#8-observability)
9. [DevOps & Deployment](#9-devops--deployment)
10. [Reliability & Disaster Recovery](#10-reliability--disaster-recovery)
11. [Cost & Operational Considerations](#11-cost--operational-considerations)
12. [Risks, Assumptions & Constraints](#12-risks-assumptions--constraints)
13. [Appendix](#13-appendix)

---

## 1. Project Overview

### 1.1 Purpose & Business Context

> _Guidance: Don't just name the system — explain the problem it solves and why it matters._

- What business problem does this system solve?
- Who are the primary stakeholders and what value does the system deliver?
- What are the measurable success criteria?
- How does this system fit into the broader organizational technology landscape?

`<Write your purpose statement here.>`

### 1.2 Scope

- **In Scope:** `<List specific features, components, and capabilities.>`
- **Out of Scope:** `<List what is excluded and why.>`
- **Future Considerations:** `<Capabilities not needed now but worth designing around — e.g., multi-tenancy, i18n, offline support, team workspaces.>`

### 1.3 Definitions & Acronyms

| Term       | Definition     |
| :--------- | :------------- |
| `<TERM_1>` | `<DEFINITION>` |
| `<TERM_2>` | `<DEFINITION>` |

---

## 2. Architectural Decisions

### 2.1 Architecture Style

| Attribute                   | Detail                                                                                            |
| :-------------------------- | :------------------------------------------------------------------------------------------------ |
| **Style**                   | `<Modular Monolith / Microservices / Serverless / Event-Driven / Hybrid>`                         |
| **Rationale**               | `<Why this style — what constraints drove the choice (team size, timeline, budget, compliance)?>` |
| **Alternatives Considered** | `<What else was evaluated and why it was rejected>`                                               |
| **Trade-offs Accepted**     | `<What downsides are you knowingly accepting>`                                                    |

### 2.2 Key Architecture Decision Records (ADRs)

> _Guidance: Document every significant technology or pattern choice. When a decision is revisited, mark the old entry as superseded rather than deleting it — the history matters._

| ID      | Decision     | Primary Rationale | Consequences              | Status   |
| :------ | :----------- | :---------------- | :------------------------ | :------- |
| ADR-001 | `<Decision>` | `<Why>`           | `<Trade-offs and impact>` | Accepted |
| ADR-002 |              |                   |                           |          |
| ADR-003 |              |                   |                           |          |

---

## 3. System Context & High-Level Architecture

### 3.1 System Context

| Element                  | Detail                                                           |
| :----------------------- | :--------------------------------------------------------------- |
| **Primary Users**        | `<User types, roles, and estimated volume>`                      |
| **External Systems**     | `<Third-party APIs consumed — payments, email, analytics, etc.>` |
| **Downstream Consumers** | `<Systems or teams that depend on this system>`                  |
| **System Boundary**      | `<What is inside vs. outside this system's responsibility>`      |

### 3.2 Architecture Diagram

> _Guidance: Insert a diagram showing all major components, communication paths with protocols labeled, which connections are synchronous vs. asynchronous, and all data stores. A C4 Container diagram works well at this level._

`<Insert architecture diagram here.>`

---

## 4. System Components

### 4.1 Project Structure Contract

> _Guidance: Define folder/module boundaries upfront. A monolith stays modular only if boundaries are enforced. A microservice stays focused only if responsibilities are clear. Adjust the structure below to fit your architecture style._

```
<Define your project structure here. Example for a monolith:>

/src
  /core              ← Pure business logic (no framework imports)
    /<domain_a>      ← Domain module: types, service, validation
    /<domain_b>      ← Domain module: types, service, validation
  /db                ← Data access layer (ORM, queries, clients)
  /lib               ← Shared utilities (auth helpers, logging, etc.)
  /transport         ← API layer (routes, controllers — thin wrappers)
```

**Key rules:**

- `<Define import rules — e.g., transport layer can import core, but core cannot import transport.>`
- `<Define what lives where — e.g., business logic must live in /core, not in route handlers.>`
- `<Define module ownership — each domain module owns its own types, validation, and service layer.>`

> _Why this matters: Without explicit boundaries, monoliths become spaghetti and microservices become distributed monoliths. Write the rules now._

### 4.2 Frontend Layer

| Attribute              | Detail                                                              |
| :--------------------- | :------------------------------------------------------------------ |
| **Framework**          | `<e.g., React, Vue, Svelte, Next.js, Nuxt, SvelteKit, HTMX, etc.>`  |
| **Language**           | `<e.g., TypeScript, JavaScript>`                                    |
| **State Management**   | `<e.g., TanStack Query, Redux, Pinia, Zustand, URL state, etc.>`    |
| **UI Library**         | `<e.g., Tailwind, MUI, Shadcn/ui, Chakra, etc.>`                    |
| **Rendering Strategy** | `<SSR / SSG / CSR / ISR / Hybrid — explain why>`                    |
| **Hosting**            | `<e.g., Vercel, Netlify, CloudFront + S3, self-hosted Nginx, etc.>` |

> _Guidance: Also note your approach to client-side error handling, accessibility targets (WCAG level), and any build tool choices that affect the architecture._

### 4.3 API Layer

| Attribute            | Detail                                                                            |
| :------------------- | :-------------------------------------------------------------------------------- |
| **Framework**        | `<e.g., Express, FastAPI, Spring Boot, .NET, Route Handlers, etc.>`               |
| **Language**         | `<e.g., TypeScript, Python, Java, Go, C#>`                                        |
| **API Type**         | `<REST / GraphQL / gRPC / Server Actions / Hybrid>`                               |
| **Validation**       | `<e.g., Zod, Pydantic, class-validator, Joi — describe where validation happens>` |
| **Error Format**     | `<Define a consistent error response shape, e.g., { error, code, details }>`      |
| **Auth Enforcement** | `<Where and how auth is checked — middleware, decorator, per-handler, etc.>`      |

> _Guidance: API handlers should orchestrate, not contain business rules. Business logic belongs in your core/service layer, not in your transport layer. This protects portability if the framework changes._

### 4.4 Database Layer

| Attribute               | Detail                                                                                            |
| :---------------------- | :------------------------------------------------------------------------------------------------ |
| **Database**            | `<e.g., PostgreSQL, MySQL, MongoDB, DynamoDB, SQLite>`                                            |
| **Hosting**             | `<e.g., Managed (RDS, Cloud SQL, Atlas, Supabase) / Self-hosted>`                                 |
| **ORM / Query Builder** | `<e.g., Drizzle, Prisma, SQLAlchemy, TypeORM, Diesel, raw SQL>`                                   |
| **Connection Pooling**  | `<e.g., pgbouncer, built-in pool config, connection limits — especially critical for serverless>` |
| **Storage**             | `<e.g., S3, GCS, Supabase Storage, local filesystem — for file/blob storage>`                     |

> _Guidance: If using serverless compute, connection pooling is not optional. Each invocation may open a new connection, and the database has a finite connection limit. Define your pooling strategy here._

### 4.5 Database Client Pattern

> _Guidance: If your authorization model is enforced at the database level (e.g., RLS, row-level policies), you likely need multiple client configurations with different permission levels. If authorization is enforced purely in application code, a single client may suffice — but document that decision._

| Client             | Permission Level                           | When to Use                                        |
| :----------------- | :----------------------------------------- | :------------------------------------------------- |
| `<default client>` | `<User-scoped / RLS-enforced / limited>`   | `<All user-facing requests — this is the default>` |
| `<admin client>`   | `<Elevated / bypasses row-level policies>` | `<Migrations, cron jobs, admin tooling only>`      |

**Rule:** `<Define when it's acceptable to use the elevated client. Any use in user-facing code should require an explicit justification in code review.>`

### 4.6 Migration Strategy

| Environment           | Method                                                       | Tooling  |
| :-------------------- | :----------------------------------------------------------- | :------- |
| **Local**             | `<e.g., auto-apply / push / manual>`                         | `<Tool>` |
| **Staging / Preview** | `<e.g., apply migration files via CI>`                       | `<Tool>` |
| **Production**        | `<e.g., manual pre-deploy step via CI — never auto-migrate>` | `<Tool>` |

> ⚠️ _Guidance: Define a clear boundary between "fast iteration" tools (acceptable locally) and "controlled migration" tools (required for shared environments). Pushing schema changes directly to shared databases without migration files causes state desync and painful debugging._

### 4.7 Caching Strategy

| Context                                | Strategy                                     | Rationale                                                     |
| :------------------------------------- | :------------------------------------------- | :------------------------------------------------------------ |
| **Authenticated / user-specific data** | `<e.g., no cache / dynamic>`                 | `<User data must never be cached and served to another user>` |
| **Public / marketing content**         | `<e.g., CDN, ISR, static generation>`        | `<Low-change content benefits from edge caching>`             |
| **API responses**                      | `<e.g., no cache / short TTL / conditional>` | `<Define default posture>`                                    |
| **Static assets**                      | `<e.g., CDN with immutable hashes>`          | `<JS, CSS, images, fonts>`                                    |

**Default posture:** `<Define your default — e.g., "everything is dynamic unless explicitly opted into caching" or "cache by default with explicit invalidation.">` Be explicit so developers don't accidentally cache user-specific data or serve stale content.

> _Guidance: If your caching behavior is tied to a specific hosting platform's features (e.g., ISR, edge caching, revalidation APIs), note that as a vendor lock-in point._

### 4.8 Service Communication

> _Guidance: Skip this section only if you have a single process with no background workers or external service calls. Otherwise, define how services talk to each other._

| Attribute                 | Detail                                                          |
| :------------------------ | :-------------------------------------------------------------- |
| **Sync Communication**    | `<e.g., REST, gRPC, direct function calls>`                     |
| **Async Communication**   | `<e.g., message queue, event bus, serverless job runner, cron>` |
| **Background Job Runner** | `<e.g., Inngest, BullMQ, Celery, SQS + Lambda, Sidekiq, none>`  |

**Timeout & Execution Constraints:**

> _Guidance: Every compute environment has execution limits. Serverless functions have timeout caps (e.g., 15s–900s depending on platform). Long-running jobs on platforms with short timeouts must be broken into smaller steps. Document your platform's limits and your strategy for working within them._

| Constraint                       | Limit        | Mitigation                                                  |
| :------------------------------- | :----------- | :---------------------------------------------------------- |
| `<e.g., API handler timeout>`    | `<Duration>` | `<e.g., offload heavy work to background jobs>`             |
| `<e.g., Background job timeout>` | `<Duration>` | `<e.g., break into sequential steps, each under the limit>` |
| `<e.g., Database query timeout>` | `<Duration>` | `<e.g., query optimization, pagination, timeout config>`    |

---

## 5. Data Flow & Integration Patterns

### 5.1 Primary Request Flow

> _Guidance: Describe the happy path for your most critical user interaction. Be specific about where auth is checked, where validation happens, and how data flows._

```
1. User action → <describe>
2. Transport layer → <routing, auth check location>
3. Validation → <where and how inputs are validated>
4. Business logic → <service layer processing>
5. Data access → <database read/write, cache check>
6. Response → <serialization, status codes, cache headers>
```

### 5.2 Asynchronous Flows

| Flow Name  | Trigger                   | Producer    | Consumer    | Failure Handling                           |
| :--------- | :------------------------ | :---------- | :---------- | :----------------------------------------- |
| `<FLOW_1>` | `<Event / Cron / Manual>` | `<Service>` | `<Service>` | `<Retry policy, dead letter queue, alert>` |
| `<FLOW_2>` |                           |             |             |                                            |

### 5.3 Third-Party Integrations

| Integration   | Purpose | Protocol                 | Fallback if Unavailable         |
| :------------ | :------ | :----------------------- | :------------------------------ |
| `<SERVICE_1>` | `<Why>` | `<REST / Webhook / SDK>` | `<What happens when it's down>` |
| `<SERVICE_2>` |         |                          |                                 |

> ⚠️ _Guidance: Every external dependency is a potential point of failure. For each integration, define what happens when it's unavailable. Also check: does your email/SMS/auth provider have rate limits that will break your flow at even modest scale?_

### 5.4 Webhook Strategy

> _Guidance: If you receive webhooks from any third-party service (payments, CRM, etc.), define these rules. Skip if not applicable._

| Attribute                  | Requirement                                                                          |
| :------------------------- | :----------------------------------------------------------------------------------- |
| **Signature Verification** | Verify webhook signature before processing any payload                               |
| **Idempotency**            | Use the event ID as an idempotency key; prevent duplicate processing                 |
| **Handler Location**       | `<Define consistent path for webhook handlers>`                                      |
| **Auth**                   | Webhook routes excluded from session auth; authenticated via provider signature only |
| **Logging**                | Log every webhook received (event type + ID) and processing result                   |

---

## 6. Security Architecture

### 6.1 Authorization Model

> _Guidance: Define this before writing any permission logic. Changing the model later means rewriting every policy, middleware guard, or RLS rule. Even if the MVP is simple (single-user isolation), document the model so the team knows when it needs to evolve._

| Attribute             | Detail                                                                                                    |
| :-------------------- | :-------------------------------------------------------------------------------------------------------- |
| **Tenancy Model**     | `<Single-tenant (user isolation) / Multi-tenant (team/org workspaces) / Hybrid>`                          |
| **Role Model**        | `<e.g., owner, member, viewer — or no roles at MVP>`                                                      |
| **Sharing Model**     | `<e.g., resources are private / shareable via invite / public by default>`                                |
| **Enforcement Layer** | `<Where permissions are checked — database (RLS), application middleware, service layer, or combination>` |
| **Admin Access**      | `<How admin/support users access the system — separate role, elevated client, dedicated admin app>`       |

**Admin & Support Access:**

> _Guidance: Decide now how admin users interact with the system. Two common approaches:_

| Approach                              | Trade-off                                                                                                 |
| :------------------------------------ | :-------------------------------------------------------------------------------------------------------- |
| **Admin role with explicit policies** | Auditable, testable, respects the same permission model. More work to set up.                             |
| **Elevated database client / bypass** | Fast to build, but bypasses permission checks entirely. Requires strict access control on who can use it. |

`<Choose one approach and document the decision here.>`

### 6.2 Authentication & Session Handling

| Attribute                       | Detail                                                                     |
| :------------------------------ | :------------------------------------------------------------------------- |
| **Auth Provider**               | `<e.g., Supabase Auth, Auth0, Cognito, Clerk, Firebase Auth, custom>`      |
| **Auth Method**                 | `<e.g., JWT + refresh tokens, session cookies, OAuth 2.0 / OIDC>`          |
| **Session Handling**            | `<e.g., HTTP-only cookies, token rotation policy, session duration>`       |
| **Session Validation Location** | `<e.g., inside API handlers, in middleware, at the gateway — explain why>` |
| **MFA**                         | `<Supported methods, enforcement policy>`                                  |

> _Guidance: Be specific about where session validation happens in the request lifecycle. If using edge/middleware for auth, note the latency implications of round-trips to your auth provider. If validating inside handlers, note how you prevent handlers from accidentally skipping validation._

### 6.3 API & Network Protection

| Attribute                  | Detail                                                                                    |
| :------------------------- | :---------------------------------------------------------------------------------------- |
| **Rate Limiting**          | `<Per-IP, per-user, per-endpoint — specify limits for auth endpoints at minimum>`         |
| **CORS**                   | `<Allowed origins policy>`                                                                |
| **CSP / Security Headers** | `<Content Security Policy, X-Frame-Options, etc.>`                                        |
| **Input Validation**       | `<Server-side validation approach — all inputs validated before reaching business logic>` |
| **Injection Prevention**   | `<e.g., parameterized queries, ORM protections, template escaping>`                       |

### 6.4 Data Protection & Secrets

| Attribute                    | Detail                                                                                |
| :--------------------------- | :------------------------------------------------------------------------------------ |
| **Encryption in Transit**    | `<e.g., TLS 1.3>`                                                                     |
| **Encryption at Rest**       | `<e.g., AES-256, provider-managed keys>`                                              |
| **Secrets Storage**          | `<e.g., environment variables, Vault, Secrets Manager — scoped per environment>`      |
| **Sensitive Key Protection** | `<How high-privilege keys (admin/service role) are restricted from developer access>` |
| **Rotation Policy**          | `<How often keys are rotated — at minimum, rotate on team member departure>`          |

### 6.5 Data Lifecycle

| Attribute              | Detail                                                                         |
| :--------------------- | :----------------------------------------------------------------------------- |
| **Deletion Strategy**  | `<Soft delete (add deleted_at) / Hard delete — and why>`                       |
| **Data Retention**     | `<e.g., soft-deleted records purged after X days>`                             |
| **User Data Deletion** | `<How a user's data is fully removed on request (GDPR / right-to-deletion)>`   |
| **Orphan Cleanup**     | `<How orphaned records (e.g., files with no parent) are detected and removed>` |

---

## 7. Testing Strategy

| Test Type                   | Tool     | Scope                                                                      | Runs When                |
| :-------------------------- | :------- | :------------------------------------------------------------------------- | :----------------------- |
| **Type Checking / Linting** | `<Tool>` | Full codebase                                                              | Every commit (CI)        |
| **Unit Tests**              | `<Tool>` | Business logic, validation schemas, utilities                              | Every commit (CI)        |
| **Integration Tests**       | `<Tool>` | API endpoints, database queries, **permission/authorization verification** | Every PR                 |
| **E2E Tests**               | `<Tool>` | Critical user paths                                                        | Pre-deploy to production |
| **Security Scans**          | `<Tool>` | Dependencies, code                                                         | Every PR or nightly      |

**Authorization testing:**

> _Guidance: If your authorization model is a core security guarantee (e.g., user data isolation), test it explicitly. At minimum, verify that User A cannot read/write User B's data. This is the single most important integration test in any system where data isolation matters._

`<Describe how authorization is tested — e.g., integration tests that query as different user roles, automated policy verification, etc.>`

> _At MVP stage, focus E2E coverage on the 2–3 flows that, if broken, would make the product unusable. Expand coverage as the product stabilizes._

---

## 8. Observability

### 8.1 Error Tracking

| Attribute                      | Detail                                                                  |
| :----------------------------- | :---------------------------------------------------------------------- |
| **Tool**                       | `<e.g., Sentry, Bugsnag, Rollbar, built-in>`                            |
| **Scope**                      | `<Client-side errors, server-side exceptions, background job failures>` |
| **Source Maps / Stack Traces** | `<How readable traces are ensured in production>`                       |

### 8.2 Logging

| Attribute         | Detail                                                                                     |
| :---------------- | :----------------------------------------------------------------------------------------- |
| **Tool**          | `<e.g., Axiom, BetterStack, ELK, CloudWatch, Loki>`                                        |
| **Format**        | Structured JSON: `timestamp`, `level`, `message`, `userId`, `requestId`                    |
| **What's Logged** | Auth events, API errors, webhook receipts, background job results, slow queries (>`<X>`ms) |
| **PII Rules**     | `<Never log passwords, tokens, full email addresses, etc.>`                                |

### 8.3 Request Correlation

| Attribute         | Detail                                                                     |
| :---------------- | :------------------------------------------------------------------------- |
| **ID Generation** | `<Where and how a requestId is generated — e.g., middleware, API gateway>` |
| **Propagation**   | `<How the ID flows across handlers, background jobs, and logs>`            |
| **Purpose**       | Trace a single user action across all processing steps during debugging    |

> _Guidance: This will save you during your first production bug. Without correlation IDs, debugging a multi-step flow means manually matching timestamps across log sources._

### 8.4 Uptime & Alerting

| Attribute             | Detail                                                                                             |
| :-------------------- | :------------------------------------------------------------------------------------------------- |
| **Uptime Monitoring** | `<Tool and check frequency>`                                                                       |
| **Alert Channels**    | `<Slack, email, SMS, PagerDuty — by severity>`                                                     |
| **Alert Triggers**    | Downtime, error rate spike (>`<X>`% over `<Y>` min), background job failure, cost threshold breach |

> _You don't need dashboards at MVP. You need to know when things break before your users tell you._

---

## 9. DevOps & Deployment

### 9.1 Source Control & Branching

| Attribute             | Detail                                               |
| :-------------------- | :--------------------------------------------------- |
| **Platform**          | `<e.g., GitHub, GitLab, Bitbucket>`                  |
| **Strategy**          | `<Trunk-based / GitFlow / GitHub Flow>`              |
| **Branch Protection** | `<Required reviews, passing CI, merge requirements>` |

### 9.2 Deployment

| Attribute               | Detail                                                                                             |
| :---------------------- | :------------------------------------------------------------------------------------------------- |
| **Platform**            | `<e.g., Vercel, AWS, Railway, Fly.io, self-hosted>`                                                |
| **Deployment Trigger**  | `<e.g., push to main, manual approval, tag-based>`                                                 |
| **Preview / Staging**   | `<e.g., per-PR preview URLs, shared staging environment>`                                          |
| **Rollback Strategy**   | `<e.g., instant rollback, redeploy previous version, blue-green swap — and how long it takes>`     |
| **Database Migrations** | `<How migrations are applied relative to deployment — manual pre-deploy step, CI-automated, etc.>` |

### 9.3 Environments

| Environment           | Purpose             | Data                         | Notes                                           |
| :-------------------- | :------------------ | :--------------------------- | :---------------------------------------------- |
| **Local**             | Development         | Seed data / mocks / local DB | `<Note any multi-service startup requirements>` |
| **Staging / Preview** | Pre-prod validation | Synthetic or anonymized      | `<Note how migrations are applied>`             |
| **Production**        | Live users          | Real data                    | `<Note access restrictions>`                    |

---

## 10. Reliability & Disaster Recovery

| Attribute               | Detail                                                                            |
| :---------------------- | :-------------------------------------------------------------------------------- |
| **Availability Target** | `<e.g., 99.9% — note if inherited from provider SLAs>`                            |
| **Backups**             | `<Method, frequency, retention period>`                                           |
| **RPO (max data loss)** | `<Duration — and confirm your backup tooling actually supports this granularity>` |
| **RTO (max downtime)**  | `<Duration — describe the restore procedure>`                                     |
| **Restore Testing**     | `<Frequency — e.g., quarterly. Document results.>`                                |

> ⚠️ _An untested backup is not a backup. Schedule a restore drill, even if it takes 30 minutes._

### Failure Scenarios

> _Guidance: You don't need a full failure mode matrix at MVP, but you should have an answer for these common scenarios:_

| Scenario                    | Impact     | Mitigation                                                       |
| :-------------------------- | :--------- | :--------------------------------------------------------------- |
| Application crash / restart | `<Impact>` | `<e.g., auto-restart, health checks, scaling>`                   |
| Database failure            | `<Impact>` | `<e.g., automated failover, replica promotion>`                  |
| Third-party API outage      | `<Impact>` | `<e.g., circuit breaker, cached fallback, graceful degradation>` |
| Auth provider outage        | `<Impact>` | `<e.g., cached sessions, degraded mode>`                         |

---

## 11. Cost & Operational Considerations

### 11.1 Monthly Cost Estimate

| Component             | Service            | Estimated Monthly Cost |
| :-------------------- | :----------------- | :--------------------- |
| **Compute / Hosting** | `<Service (tier)>` | `<$X>`                 |
| **Database**          | `<Service (tier)>` | `<$X>`                 |
| **Auth**              | `<Service (tier)>` | `<$X>`                 |
| **Email / SMS**       | `<Service (tier)>` | `<$X>`                 |
| **Error Tracking**    | `<Service (tier)>` | `<$X>`                 |
| **Logging**           | `<Service (tier)>` | `<$X>`                 |
| **Background Jobs**   | `<Service (tier)>` | `<$X>`                 |
| **Total**             |                    | **$X/month**           |

> _Guidance: Don't forget email/SMS providers. Many auth platforms have aggressive rate limits on their built-in email sending that will break your flow at even modest scale._

### 11.2 Scaling Cost Triggers

> _Guidance: Know when you'll hit the next pricing tier so it doesn't surprise you._

| Trigger                         | Threshold | Action                       |
| :------------------------------ | :-------- | :--------------------------- |
| `<e.g., Bandwidth>`             | `<Limit>` | `<Upgrade plan or optimize>` |
| `<e.g., Database size>`         | `<Limit>` | `<Archive or upgrade>`       |
| `<e.g., Connection count>`      | `<Limit>` | `<Verify pooling, optimize>` |
| `<e.g., Error tracking volume>` | `<Limit>` | `<Fix sources or upgrade>`   |
| `<e.g., Background job runs>`   | `<Limit>` | `<Evaluate paid tier>`       |

### 11.3 Vendor Lock-in Assessment

| Component      | Lock-in Risk        | What's Portable            | What's Not                  |
| :------------- | :------------------ | :------------------------- | :-------------------------- |
| `<PROVIDER_1>` | Low / Medium / High | `<What transfers cleanly>` | `<What requires rewriting>` |
| `<PROVIDER_2>` |                     |                            |                             |
| `<PROVIDER_3>` |                     |                            |                             |

> _Guidance: Be honest. "We use standard SQL via an ORM" is portable. "We rely on this provider's proprietary caching/auth/realtime features" is not. Accepting lock-in is fine — just do it consciously and note what a migration would actually cost._

---

## 12. Risks, Assumptions & Constraints

### 12.1 Assumptions

| Assumption                                                         | Impact if Wrong                                           |
| :----------------------------------------------------------------- | :-------------------------------------------------------- |
| `<e.g., Traffic stays below X for Y months>`                       | `<Would need to revisit scaling and infrastructure tier>` |
| `<e.g., Team stays at X developers>`                               | `<Larger team needs stricter boundaries, API contracts>`  |
| `<e.g., Authorization stays simple (no teams/roles) for X months>` | `<Permission model needs significant rework>`             |

### 12.2 Constraints

| Constraint                           | Source     | Impact on Architecture                             |
| :----------------------------------- | :--------- | :------------------------------------------------- |
| `<e.g., Budget capped at $X/month>`  | Business   | `<Limits infrastructure choices>`                  |
| `<e.g., Must use existing database>` | Legacy     | `<Constrains ORM and migration strategy>`          |
| `<e.g., Compliance requirement>`     | Regulatory | `<Encryption, audit, data residency requirements>` |

### 12.3 Risks

| Risk                                                    | Likelihood | Impact       | Mitigation                                                        |
| :------------------------------------------------------ | :--------- | :----------- | :---------------------------------------------------------------- |
| `<e.g., Permission misconfiguration exposes user data>` | Medium     | **Critical** | `<Automated integration tests verify data isolation on every PR>` |
| `<e.g., Provider outage during launch>`                 | Low        | High         | `<Cached pages served; status communicated to users>`             |
| `<e.g., Background job exceeds execution timeout>`      | Medium     | Medium       | `<Jobs broken into steps; enforced in code review>`               |
| `<e.g., DB connection exhaustion under load>`           | Low        | High         | `<Connection pooling configured; limits monitored>`               |
| `<e.g., Scaling past free tiers before revenue>`        | Medium     | Medium       | `<Cost triggers and alerts configured>`                           |

---

## 13. Appendix

| Document                         | Location         |
| :------------------------------- | :--------------- |
| ADR files                        | `<Path or link>` |
| Database schema                  | `<Path or link>` |
| API route inventory              | `<Path or link>` |
| Environment variable reference   | `<Path or link>` |
| Authorization policy definitions | `<Path or link>` |
| Webhook handler inventory        | `<Path or link>` |
| Runbooks                         | `<Path or link>` |

### Revision History

| Version | Date     | Author     | Changes       |
| :------ | :------- | :--------- | :------------ |
| 0.1     | `<Date>` | `<Author>` | Initial draft |
|         |          |            |               |

---

_This document should be reviewed whenever a new integration is added, a scaling threshold is hit, the authorization model changes, or a significant architectural decision is made._
