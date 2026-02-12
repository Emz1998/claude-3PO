# 📐 Development Architecture Document

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
5. [Data Architecture](#5-data-architecture)
6. [Data Flow & Integration Patterns](#6-data-flow--integration-patterns)
7. [Security Architecture](#7-security-architecture)
8. [Scalability & Performance](#8-scalability--performance)
9. [Reliability & Disaster Recovery](#9-reliability--disaster-recovery)
10. [DevOps & CI/CD](#10-devops--cicd)
11. [Logging, Monitoring & Observability](#11-logging-monitoring--observability)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Cost & Operational Considerations](#13-cost--operational-considerations)
14. [Risks, Assumptions & Constraints](#14-risks-assumptions--constraints)
15. [Appendix](#15-appendix)

---

## 1. Project Overview

### 1.1 Purpose & Business Context

> _Guidance: Don't just name the system — explain the problem it solves and why it matters._

- What business problem does this system solve?
- Who are the primary stakeholders and what value does the system deliver to them?
- What are the measurable success criteria (e.g., reduce processing time by 40%, support 10K concurrent users)?
- How does this system fit into the broader organizational technology landscape?

`<Write your purpose statement here.>`

### 1.2 Scope

**In Scope:**

- `<FEATURE_OR_COMPONENT_1>`
- `<FEATURE_OR_COMPONENT_2>`

**Out of Scope:**

- `<EXCLUDED_FEATURE_1>` — _Reason: `<why excluded>`_
- `<EXCLUDED_FEATURE_2>` — _Reason: `<why excluded>`_

**Future Considerations:**

> _Guidance: Capabilities that are out of scope today but should influence architectural decisions (e.g., multi-tenancy, internationalization, offline support)._

- `<FUTURE_CAPABILITY_1>`
- `<FUTURE_CAPABILITY_2>`

### 1.3 Definitions & Acronyms

| Term       | Definition     |
| ---------- | -------------- |
| `<TERM_1>` | `<DEFINITION>` |
| `<TERM_2>` | `<DEFINITION>` |

---

## 2. Architectural Decisions

### 2.1 Architecture Style

| Attribute                   | Detail                                                          |
| --------------------------- | --------------------------------------------------------------- |
| **Style**                   | Monolithic / Microservices / Serverless / Event-Driven / Hybrid |
| **Rationale**               | `<Why this style was chosen over alternatives>`                 |
| **Alternatives Considered** | `<What else was evaluated and why it was rejected>`             |
| **Trade-offs Accepted**     | `<What downsides are you knowingly accepting>`                  |

> _Guidance: Be specific about constraints that drove this choice — team size, timeline, budget, compliance requirements, existing infrastructure._

### 2.2 Key Architecture Decision Records Summary(ADRs)

> _Guidance: Document every significant technology or pattern choice. When a decision is revisited, mark the old entry as superseded rather than deleting it — the history matters._

| ID                                    | Decision                   | Primary Rationale                    | Status                |
| :------------------------------------ | :------------------------- | :----------------------------------- | :-------------------- |
| **[ADR-001](./decisions/adr-001.md)** | Event-Driven Microservices | Scalability for high-burst traffic   | Accepted              |
| **[ADR-004](./decisions/adr-004.md)** | Next.js (App Router)       | SEO requirements + SSR performance   | Accepted              |
| **[ADR-007](./decisions/adr-007.md)** | Auth0 for Identity         | Reduced maintenance vs. custom OAuth | Superseded by ADR-012 |

---

## 3. System Context & High-Level Architecture

### 3.1 System Context

| Element                  | Description                                                    |
| ------------------------ | -------------------------------------------------------------- |
| **Primary Users**        | `<User types, roles, and estimated volumes>`                   |
| **External Systems**     | `<Third-party integrations, APIs consumed, SaaS dependencies>` |
| **Downstream Consumers** | `<Systems or teams that depend on this system's APIs or data>` |
| **Core System Boundary** | `<What is inside vs. outside this system's responsibility>`    |

> _Guidance: Include a C4 Level 1 (System Context) diagram showing your system, its users, and all external dependencies._

### 3.2 Architecture Diagram

> _Guidance: Insert a C4 Level 2 (Container) diagram or equivalent. The diagram should show:_
>
> - _All major components and their responsibilities_
> - _Communication paths with protocols labeled (HTTPS, gRPC, AMQP, etc.)_
> - _Which connections are synchronous vs. asynchronous_
> - _Data stores and caches_

`<Insert architecture diagram here>`

---

## 4. System Components

### 4.1 Frontend Layer

| Attribute              | Detail                                                  |
| ---------------------- | ------------------------------------------------------- |
| **Framework**          | `<e.g., React 18, Next.js 14, Vue 3, SvelteKit>`        |
| **Language**           | `<e.g., TypeScript 5.x>`                                |
| **State Management**   | `<e.g., Zustand, Redux Toolkit, Pinia, TanStack Query>` |
| **UI Library**         | `<e.g., Tailwind CSS, Shadcn/ui, MUI>`                  |
| **Build Tool**         | `<e.g., Vite, Webpack, Turbopack>`                      |
| **Rendering Strategy** | `<SSR / SSG / CSR / ISR — explain why>`                 |
| **Hosting**            | `<e.g., Vercel, CloudFront + S3, Nginx>`                |

> _Guidance: Also address the following:_
>
> - _How is client-side error handling managed (error boundaries, Sentry, etc.)?_
> - _What is the accessibility (a11y) strategy and target conformance level (WCAG 2.1 AA)?_
> - _How is the frontend tested (unit, integration, visual regression)?_

### 4.2 Backend Layer

| Attribute          | Detail                                                           |
| ------------------ | ---------------------------------------------------------------- |
| **Framework**      | `<e.g., Express, FastAPI, Spring Boot, .NET 8>`                  |
| **Language**       | `<e.g., Node.js 20, Python 3.12, Java 21, Go 1.22>`              |
| **API Type**       | REST / GraphQL / gRPC / Hybrid                                   |
| **API Versioning** | `<e.g., URL path /v1/, header-based, query param>`               |
| **Authentication** | `<e.g., JWT with refresh token rotation, OAuth 2.0 + OIDC>`      |
| **Authorization**  | `<e.g., RBAC with Casbin, ABAC with OPA>`                        |
| **Validation**     | `<e.g., Zod, Pydantic, class-validator>`                         |
| **Business Logic** | `<Service layer patterns — hexagonal, clean architecture, etc.>` |

> _Guidance: Go deeper on auth:_
>
> - _Describe token lifecycle: issuance, refresh, rotation, and revocation._
> - _How are permissions modeled? What happens when a user's role changes mid-session?_
> - _What patterns handle cross-cutting concerns (logging, auth, rate limiting)? Middleware? Decorators? Interceptors?_

### 4.3 Database Layer

| Attribute               | Detail                                                                      |
| ----------------------- | --------------------------------------------------------------------------- |
| **Primary Database**    | `<e.g., PostgreSQL 16, MongoDB 7, MySQL 8>`                                 |
| **Database Type**       | Relational / Document / Key-Value / Graph / Time-Series                     |
| **Hosting**             | `<e.g., AWS RDS, Cloud SQL, Atlas, Self-hosted>`                            |
| **ORM / Query Builder** | `<e.g., Prisma, Drizzle, SQLAlchemy, TypeORM>`                              |
| **Migration Strategy**  | `<e.g., Prisma Migrate, Flyway, Alembic — describe zero-downtime approach>` |
| **Read Replicas**       | `<Yes / No — describe routing strategy if applicable>`                      |
| **Connection Pooling**  | `<e.g., PgBouncer, built-in pool config, connection limits>`                |
| **Backup Strategy**     | `<e.g., daily snapshots, PITR, retention period>`                           |
| **Data Retention**      | `<Archival and purge policies>`                                             |

> _Guidance: If using multiple data stores (e.g., PostgreSQL + Redis + Elasticsearch), explain the role of each and how data consistency is maintained across them. Describe your indexing strategy for high-traffic queries._

### 4.4 Service Communication

> _Guidance: This section is critical for any system with more than one backend service. Skip only if truly monolithic with a single process._

| Attribute               | Detail                                          |
| ----------------------- | ----------------------------------------------- |
| **Sync Communication**  | `<e.g., REST over HTTPS, gRPC with TLS>`        |
| **Async Communication** | `<e.g., RabbitMQ, Kafka, SQS, Redis Streams>`   |
| **Message Format**      | `<e.g., JSON, Protobuf, Avro>`                  |
| **Service Discovery**   | `<e.g., Consul, Kubernetes DNS, AWS Cloud Map>` |
| **API Gateway**         | `<e.g., Kong, AWS API Gateway, Traefik>`        |

**Resilience Patterns:**

| Pattern               | Implementation                                                 |
| --------------------- | -------------------------------------------------------------- |
| **Circuit Breaker**   | `<e.g., resilience4j, Polly, opossum>`                         |
| **Retry Policy**      | `<e.g., exponential backoff, max 3 retries, idempotency keys>` |
| **Timeout Strategy**  | `<Default and per-service timeouts>`                           |
| **Bulkhead**          | `<Thread/connection pool isolation strategy>`                  |
| **Dead Letter Queue** | `<How failed messages are handled>`                            |

### 4.5 Infrastructure Layer

| Attribute              | Detail                                                  |
| ---------------------- | ------------------------------------------------------- |
| **Cloud Provider**     | AWS / Azure / GCP / On-Premise / Hybrid                 |
| **Containerization**   | `<e.g., Docker, Podman, None>`                          |
| **Orchestration**      | `<e.g., Kubernetes, ECS, Cloud Run, None>`              |
| **IaC Tool**           | `<e.g., Terraform, Pulumi, CloudFormation, CDK>`        |
| **DNS / CDN**          | `<e.g., CloudFlare, CloudFront, Route 53>`              |
| **Secrets Management** | `<e.g., AWS Secrets Manager, HashiCorp Vault, Doppler>` |

---

## 5. Data Architecture

> _Guidance: This section ensures data is treated as a first-class architectural concern, not an afterthought buried in the database table._

### 5.1 Data Model Overview

> _Guidance: Include or reference an ER diagram. Describe the core domain entities, their relationships, and any bounded contexts if using DDD._

`<Insert ER diagram or link to it>`

### 5.2 Data Store Mapping

| Data Type             | Store                        | Justification                                |
| --------------------- | ---------------------------- | -------------------------------------------- |
| Transactional data    | `<e.g., PostgreSQL>`         | `<ACID compliance, relational integrity>`    |
| Session / cache       | `<e.g., Redis>`              | `<Low latency, TTL support>`                 |
| Full-text search      | `<e.g., Elasticsearch>`      | `<Complex query needs, faceted search>`      |
| File / blob storage   | `<e.g., S3, GCS>`            | `<Cost-efficient unstructured storage>`      |
| Analytics / reporting | `<e.g., BigQuery, Redshift>` | `<Columnar storage for aggregation queries>` |
| Event log             | `<e.g., Kafka, EventStore>`  | `<Ordered, immutable event stream>`          |

### 5.3 Data Consistency Strategy

> _Guidance: Address the following:_
>
> - _Is eventual consistency acceptable for any data paths? Which ones?_
> - _How are cross-service data operations handled (sagas, two-phase commit, outbox pattern)?_
> - _How do you handle cache invalidation?_

`<Describe your consistency strategy here.>`

### 5.4 Data Migration & Seeding

> _Guidance: How do schema changes get applied in production? How is seed data managed across environments?_

`<Describe migration and seeding approach here.>`

---

## 6. Data Flow & Integration Patterns

### 6.1 Primary Request Flow

> _Guidance: Describe the happy path for your most critical user interaction. Be specific about protocols, auth checks, and data transformations at each step._

```
1. User action → <describe>
2. CDN / Load Balancer → <routing logic>
3. API Gateway → <auth validation, rate limiting>
4. Application Service → <business logic, validation>
5. Database / Cache → <read/write strategy>
6. Response transformation → <serialization, pagination>
7. Response returned → <caching headers, status codes>
```

### 6.2 Asynchronous Flows

| Flow Name  | Trigger                   | Producer    | Consumer    | Processing       | Failure Handling        |
| ---------- | ------------------------- | ----------- | ----------- | ---------------- | ----------------------- |
| `<FLOW_1>` | `<Event / Cron / Manual>` | `<Service>` | `<Service>` | `<What it does>` | `<Retry / DLQ / Alert>` |
| `<FLOW_2>` |                           |             |             |                  |                         |

### 6.3 Third-Party Integrations

| Integration   | Purpose | Protocol             | Auth Method       | SLA Dependency       | Fallback Behavior               |
| ------------- | ------- | -------------------- | ----------------- | -------------------- | ------------------------------- |
| `<SERVICE_1>` | `<Why>` | `<REST/Webhook/SDK>` | `<API key/OAuth>` | `<Uptime guarantee>` | `<What happens when it's down>` |
| `<SERVICE_2>` |         |                      |                   |                      |                                 |

> ⚠️ **WARNING:** Every external dependency is a potential point of failure. For each integration, define what happens when it is unavailable for 1 minute, 1 hour, and 1 day.

### 6.4 Background Jobs & Scheduled Tasks

| Job Name  | Schedule            | Purpose          | Idempotent? | Timeout      | Alerting                      |
| --------- | ------------------- | ---------------- | ----------- | ------------ | ----------------------------- |
| `<JOB_1>` | `<Cron expression>` | `<What it does>` | Yes / No    | `<Duration>` | `<How failures are reported>` |
| `<JOB_2>` |                     |                  |             |              |                               |

---

## 7. Security Architecture

### 7.1 Authentication & Authorization

| Attribute                 | Detail                                                  |
| ------------------------- | ------------------------------------------------------- |
| **Authentication Method** | `<e.g., JWT + refresh tokens, OAuth 2.0 / OIDC, SAML>`  |
| **Identity Provider**     | `<e.g., Auth0, Cognito, Keycloak, custom>`              |
| **Session Management**    | `<Token rotation policy, session duration, revocation>` |
| **Authorization Model**   | `<RBAC / ABAC / ReBAC — describe permission model>`     |
| **MFA**                   | `<Supported methods, enforcement policy>`               |

### 7.2 Data Protection

| Attribute                 | Detail                                               |
| ------------------------- | ---------------------------------------------------- |
| **Encryption in Transit** | `<e.g., TLS 1.3, mTLS between services>`             |
| **Encryption at Rest**    | `<e.g., AES-256, KMS-managed keys>`                  |
| **PII Handling**          | `<How PII is identified, classified, and protected>` |
| **Data Masking**          | `<Masking strategy for logs, non-prod environments>` |

### 7.3 API & Network Security

| Attribute                | Detail                                                    |
| ------------------------ | --------------------------------------------------------- |
| **Rate Limiting**        | `<Per-user, per-IP, tiered by plan>`                      |
| **WAF**                  | `<e.g., AWS WAF, Cloudflare, ModSecurity>`                |
| **CORS Policy**          | `<Allowed origins strategy>`                              |
| **Input Validation**     | `<Server-side validation approach, injection prevention>` |
| **Network Segmentation** | `<VPC layout, private subnets, security groups>`          |

### 7.4 Secrets & Credentials

| Attribute           | Detail                                                  |
| ------------------- | ------------------------------------------------------- |
| **Secrets Manager** | `<e.g., HashiCorp Vault, AWS Secrets Manager, Doppler>` |
| **Rotation Policy** | `<How and how often secrets are rotated>`               |
| **CI/CD Secrets**   | `<How secrets are injected into pipelines>`             |

### 7.5 Audit & Compliance

| Attribute                  | Detail                                                      |
| -------------------------- | ----------------------------------------------------------- |
| **Audit Logging**          | `<What is logged: auth events, data access, admin actions>` |
| **Log Retention**          | `<Duration, immutability guarantees>`                       |
| **Compliance Standards**   | `<e.g., SOC 2, HIPAA, GDPR, PCI-DSS>`                       |
| **Vulnerability Scanning** | `<e.g., Snyk, Dependabot, Trivy — frequency>`               |
| **Penetration Testing**    | `<Frequency and scope>`                                     |

---

## 8. Scalability & Performance

### 8.1 Capacity Planning

| Attribute                      | Detail                 |
| ------------------------------ | ---------------------- |
| **Expected Users (launch)**    | `<Number>`             |
| **Expected Users (12 months)** | `<Number>`             |
| **Peak Concurrent Users**      | `<Number>`             |
| **Data Growth Rate**           | `<e.g., ~500GB/month>` |

### 8.2 Scaling Strategy

| Component            | Strategy                                  | Trigger                                   |
| -------------------- | ----------------------------------------- | ----------------------------------------- |
| **Application Tier** | Horizontal / Vertical                     | `<e.g., CPU > 70% for 5 min>`             |
| **Database**         | `<Read replicas, sharding, partitioning>` | `<e.g., connection count, query latency>` |
| **Cache**            | `<Cluster scaling, eviction policy>`      | `<e.g., memory utilization > 80%>`        |
| **Message Queue**    | `<Partition scaling, consumer groups>`    | `<e.g., queue depth > threshold>`         |

### 8.3 Caching Strategy

| Cache Layer     | Technology                                | TTL          | Invalidation Strategy               |
| --------------- | ----------------------------------------- | ------------ | ----------------------------------- |
| **CDN**         | `<e.g., CloudFront, Cloudflare>`          | `<Duration>` | `<Purge API, versioned URLs>`       |
| **Application** | `<e.g., Redis, Memcached>`                | `<Duration>` | `<Write-through, event-based, TTL>` |
| **Database**    | `<e.g., query cache, materialized views>` | `<Duration>` | `<Refresh schedule>`                |

### 8.4 Performance Targets

| Metric                            | Target             | Measurement Method |
| --------------------------------- | ------------------ | ------------------ |
| **P50 Response Time**             | `<X ms>`           | `<e.g., APM tool>` |
| **P99 Response Time**             | `<X ms>`           |                    |
| **Throughput**                    | `<X requests/sec>` |                    |
| **Error Rate**                    | `<X%>`             |                    |
| **Time to First Byte**            | `<X ms>`           |                    |
| **Core Web Vitals (LCP/FID/CLS)** | `<Targets>`        |                    |

---

## 9. Reliability & Disaster Recovery

> _Guidance: This section is not optional. Every production system needs explicit answers here._

### 9.1 Availability Targets

| Attribute                          | Detail                                                     |
| ---------------------------------- | ---------------------------------------------------------- |
| **Availability Target**            | `<e.g., 99.9% (8.76h downtime/year)>`                      |
| **Planned Maintenance Window**     | `<e.g., Sundays 2–4 AM UTC, or zero-downtime deployments>` |
| **RTO (Recovery Time Objective)**  | `<Maximum acceptable downtime after failure>`              |
| **RPO (Recovery Point Objective)** | `<Maximum acceptable data loss measured in time>`          |

### 9.2 Failure Modes & Mitigation

| Failure Scenario                  | Impact     | Mitigation                                 | Recovery Procedure                 |
| --------------------------------- | ---------- | ------------------------------------------ | ---------------------------------- |
| Single application instance crash | `<Impact>` | `<e.g., auto-scaling, health checks>`      | `<Automatic / manual steps>`       |
| Database primary failure          | `<Impact>` | `<e.g., automated failover to replica>`    | `<Failover time, data validation>` |
| Third-party API outage            | `<Impact>` | `<e.g., circuit breaker, cached fallback>` | `<Degraded mode behavior>`         |
| Full region outage                | `<Impact>` | `<e.g., multi-region active-passive>`      | `<DNS failover, data sync>`        |
| Data corruption                   | `<Impact>` | `<e.g., immutable audit log, PITR>`        | `<Restore procedure, validation>`  |

### 9.3 Backup & Restore

| Data Store | Backup Method                 | Frequency    | Retention    | Restore Tested?    |
| ---------- | ----------------------------- | ------------ | ------------ | ------------------ |
| `<DB_1>`   | `<Snapshot / PITR / Logical>` | `<Schedule>` | `<Duration>` | `<Last test date>` |
| `<DB_2>`   |                               |              |              |                    |

> ⚠️ **WARNING:** A backup that has never been restored is not a backup — it's a hope. Schedule regular restore drills and document the results.

### 9.4 Incident Response

| Attribute                 | Detail                                           |
| ------------------------- | ------------------------------------------------ |
| **On-call Rotation**      | `<Tool and schedule>`                            |
| **Escalation Path**       | `<L1 → L2 → L3 with timeframes>`                 |
| **Runbook Location**      | `<Where runbooks are stored>`                    |
| **Post-incident Process** | `<Blameless retrospective cadence and template>` |

---

## 10. DevOps & CI/CD

### 10.1 Source Control

| Attribute               | Detail                                                  |
| ----------------------- | ------------------------------------------------------- |
| **Platform**            | `<e.g., GitHub, GitLab, Bitbucket>`                     |
| **Branching Strategy**  | `<Trunk-based / GitFlow / GitHub Flow>`                 |
| **Branch Protection**   | `<Required reviews, status checks, merge requirements>` |
| **Monorepo / Polyrepo** | `<Approach and rationale>`                              |

### 10.2 CI/CD Pipeline

| Attribute               | Detail                                        |
| ----------------------- | --------------------------------------------- |
| **CI Tool**             | `<e.g., GitHub Actions, GitLab CI, CircleCI>` |
| **CD Tool**             | `<Same or different from CI>`                 |
| **Deployment Strategy** | Blue/Green / Canary / Rolling / Feature Flags |
| **Rollback Strategy**   | `<Automated or manual, time to rollback>`     |
| **Artifact Storage**    | `<e.g., ECR, Artifactory, GitHub Packages>`   |

### 10.3 Environments

| Environment    | Purpose                | Data                   | Access           |
| -------------- | ---------------------- | ---------------------- | ---------------- |
| **Local**      | Developer workstations | Seed data / mocks      | All developers   |
| **Dev**        | Integration testing    | Synthetic              | Engineering team |
| **Staging**    | Pre-prod validation    | Anonymized prod mirror | Engineering + QA |
| **Production** | Live users             | Real data              | Restricted       |

### 10.4 Testing Strategy

| Test Type             | Tool                                | Coverage Target | Runs When             |
| --------------------- | ----------------------------------- | --------------- | --------------------- |
| **Unit Tests**        | `<e.g., Jest, pytest, JUnit>`       | `<e.g., 80%>`   | Every commit          |
| **Integration Tests** | `<e.g., Supertest, TestContainers>` |                 | Every PR              |
| **E2E Tests**         | `<e.g., Playwright, Cypress>`       |                 | Pre-deploy to staging |
| **Contract Tests**    | `<e.g., Pact, Protolock>`           |                 | PR + nightly          |
| **Load Tests**        | `<e.g., k6, Locust, Artillery>`     |                 | Pre-release           |
| **Security Scans**    | `<e.g., Snyk, SAST/DAST tools>`     |                 | Every PR + nightly    |

### 10.5 Feature Flags

| Attribute              | Detail                                             |
| ---------------------- | -------------------------------------------------- |
| **Tool**               | `<e.g., LaunchDarkly, Unleash, Flagsmith, custom>` |
| **Flag Lifecycle**     | `<How flags are created, tested, and retired>`     |
| **Stale Flag Cleanup** | `<Process for removing old flags>`                 |

---

## 11. Logging, Monitoring & Observability

### 11.1 Observability Stack

| Layer              | Tool                                        | Purpose                     |
| ------------------ | ------------------------------------------- | --------------------------- |
| **Logging**        | `<e.g., ELK, Loki, CloudWatch Logs>`        | Structured application logs |
| **Metrics**        | `<e.g., Prometheus, Datadog, CloudWatch>`   | System and business metrics |
| **Tracing**        | `<e.g., Jaeger, Tempo, X-Ray>`              | Distributed request tracing |
| **APM**            | `<e.g., Datadog APM, New Relic, Dynatrace>` | Application performance     |
| **Error Tracking** | `<e.g., Sentry, Bugsnag>`                   | Exception aggregation       |

### 11.2 Logging Standards

| Attribute          | Detail                                         |
| ------------------ | ---------------------------------------------- |
| **Log Format**     | `<e.g., structured JSON with correlation IDs>` |
| **Log Levels**     | `<When to use DEBUG, INFO, WARN, ERROR>`       |
| **Sensitive Data** | `<PII scrubbing/masking rules>`                |
| **Retention**      | `<Hot: X days, Warm: X days, Cold: X days>`    |

### 11.3 Alerting

| Attribute                 | Detail                                          |
| ------------------------- | ----------------------------------------------- |
| **Alerting Tool**         | `<e.g., PagerDuty, OpsGenie, Grafana Alerting>` |
| **Alert Severity Levels** | `<P1–P4 definitions and response SLAs>`         |
| **Notification Channels** | `<Slack, email, phone, SMS — by severity>`      |

> _Guidance: Define SLIs (Service Level Indicators) and SLOs (Service Level Objectives) for your most critical user journeys. Example: "95% of checkout API calls complete in under 500ms measured over a 28-day rolling window."_

### 11.4 Dashboards

| Dashboard            | Audience             | Key Metrics                        |
| -------------------- | -------------------- | ---------------------------------- |
| **System Health**    | Engineering          | CPU, memory, error rate, latency   |
| **Business Metrics** | Product / Leadership | Signups, conversions, active users |
| **SLO Burn Rate**    | On-call              | Error budget consumption           |

---

## 12. Non-Functional Requirements

| Category                 | Requirement                                    | How It's Achieved                           |
| ------------------------ | ---------------------------------------------- | ------------------------------------------- |
| **Availability**         | `<e.g., 99.9% uptime>`                         | `<Multi-AZ, health checks, auto-failover>`  |
| **Performance**          | `<e.g., P95 < 200ms>`                          | `<Caching, CDN, query optimization>`        |
| **Security**             | `<e.g., SOC 2 Type II>`                        | `<Encryption, audit logs, access controls>` |
| **Scalability**          | `<e.g., 10x traffic in 12 months>`             | `<Horizontal scaling, async processing>`    |
| **Maintainability**      | `<e.g., new developer productive in < 1 week>` | `<Documentation, modular design, testing>`  |
| **Accessibility**        | `<e.g., WCAG 2.1 AA>`                          | `<Semantic HTML, ARIA, automated testing>`  |
| **Compliance**           | `<e.g., GDPR, HIPAA, PCI-DSS>`                 | `<Data handling, consent, encryption>`      |
| **Internationalization** | `<e.g., support 5 languages by Q4>`            | `<i18n framework, locale-aware data>`       |

---

## 13. Cost & Operational Considerations

### 13.1 Infrastructure Cost Estimate

| Component            | Service                         | Estimated Monthly Cost | Notes |
| -------------------- | ------------------------------- | ---------------------- | ----- |
| **Compute**          | `<e.g., 3x t3.large>`           | `<$X>`                 |       |
| **Database**         | `<e.g., RDS db.r6g.large>`      | `<$X>`                 |       |
| **Cache**            | `<e.g., ElastiCache r6g.large>` | `<$X>`                 |       |
| **Storage**          | `<e.g., S3 Standard 500GB>`     | `<$X>`                 |       |
| **CDN / Networking** | `<e.g., CloudFront>`            | `<$X>`                 |       |
| **Monitoring**       | `<e.g., Datadog Pro>`           | `<$X>`                 |       |
| **Third-Party SaaS** | `<e.g., Auth0, LaunchDarkly>`   | `<$X>`                 |       |
| **Total**            |                                 | **$X/month**           |       |

### 13.2 Cost Optimization Strategy

> _Guidance: Describe reserved instances, spot instances, auto-scaling down during off-peak, storage tiering, and any cost alerts or budgets configured._

`<Describe your cost optimization approach here.>`

### 13.3 Vendor Lock-in Assessment

| Component          | Lock-in Risk | Mitigation                                       |
| ------------------ | ------------ | ------------------------------------------------ |
| `<e.g., DynamoDB>` | High         | `<e.g., abstract via repository pattern>`        |
| `<e.g., S3>`       | Low          | `<e.g., S3-compatible API is industry standard>` |

---

## 14. Risks, Assumptions & Constraints

### 14.1 Assumptions

> _Guidance: State what you're taking for granted. If an assumption proves wrong, which architectural decisions would need to change?_

| Assumption                                          | Impact if Wrong                                        |
| --------------------------------------------------- | ------------------------------------------------------ |
| `<e.g., Peak traffic won't exceed 5x average>`      | `<Would need to revisit scaling strategy and DB tier>` |
| `<e.g., Team will have Kubernetes expertise by Q2>` | `<Would need to fall back to managed PaaS>`            |
| `<ASSUMPTION_3>`                                    |                                                        |

### 14.2 Constraints

| Constraint                            | Source     | Impact on Architecture                             |
| ------------------------------------- | ---------- | -------------------------------------------------- |
| `<e.g., Budget capped at $5K/month>`  | Business   | `<Limits cloud resource choices>`                  |
| `<e.g., Must use existing Oracle DB>` | Legacy     | `<Constrains ORM and migration strategy>`          |
| `<e.g., HIPAA compliance required>`   | Regulatory | `<Encryption, audit, data residency requirements>` |

### 14.3 Risks

| Risk                                                       | Likelihood | Impact | Mitigation                                              |
| ---------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------- |
| `<e.g., Third-party payment API rate limits hit at scale>` | Medium     | High   | `<Queue-based processing, multiple provider support>`   |
| `<e.g., Team unfamiliar with chosen framework>`            | High       | Medium | `<Training budget, pair programming, gradual adoption>` |
| `<RISK_3>`                                                 |            |        |                                                         |

---

## 15. Appendix

### 15.1 Reference Documents

| Document                    | Location |
| --------------------------- | -------- |
| ER Diagram                  | `<Link>` |
| API Specification (OpenAPI) | `<Link>` |
| Infrastructure Diagram      | `<Link>` |
| Runbooks                    | `<Link>` |
| ADR Repository              | `<Link>` |

### 15.2 Revision History

| Version | Date     | Author     | Changes       |
| ------- | -------- | ---------- | ------------- |
| 0.1     | `<Date>` | `<Author>` | Initial draft |
|         |          |            |               |

---

_This document should be treated as a living artifact. Review and update it at least quarterly, or whenever a significant architectural change is made._
