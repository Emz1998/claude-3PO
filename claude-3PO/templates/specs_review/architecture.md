# Architecture Review Report Template

## 1. Executive Summary

**Project name:** [Project Name]
**Review date:** [Date]
**Reviewer(s):** [Name(s)]
**Architecture status:** [Approved / Approved with conditions / Needs revision / Rejected]

### Summary

[Briefly describe what was reviewed, the overall quality of the architecture, and the most important findings.]

### Overall Rating

**Architecture rating:** [0–10] / 10

### Final Recommendation

[State whether the architecture should proceed, proceed with conditions, or be revised before implementation.]

---

## 2. Project Context

### Product Overview

[Describe what the product does and who it is for.]

### Business Goals

- [Goal 1]
- [Goal 2]
- [Goal 3]

### Technical Goals

- [Goal 1]
- [Goal 2]
- [Goal 3]

### Non-Goals

- [Non-goal 1]
- [Non-goal 2]
- [Non-goal 3]

---

## 3. Architecture Overview

### High-Level System Description

[Describe the architecture in plain language. Explain the major parts of the system and how they interact.]

### High-Level Architecture Diagram

```text
[Client Apps]
     |
     v
[API Gateway / Backend]
     |
     +-- [Service A]
     +-- [Service B]
     +-- [Service C]
     |
     v
[Databases / Storage / External Services]
```

### Main Components

| Component     | Responsibility | Notes               |
| ------------- | -------------- | ------------------- |
| [Component 1] | [What it does] | [Important details] |
| [Component 2] | [What it does] | [Important details] |
| [Component 3] | [What it does] | [Important details] |

---

## 4. Data Architecture

### Main Data Stores

| Data Store           | Purpose   | Data Type                             | Owner          |
| -------------------- | --------- | ------------------------------------- | -------------- |
| [Database / Storage] | [Purpose] | [Relational / NoSQL / Object / Cache] | [Service/team] |

### Core Entities

- [Entity 1]
- [Entity 2]
- [Entity 3]

### Data Flow

[Explain how data moves through the system. Include important reads, writes, events, and background jobs.]

### Data Risks

- [Risk 1]
- [Risk 2]
- [Risk 3]

---

## 5. API and Integration Review

### Internal APIs

| API / Service | Consumer   | Purpose   | Notes   |
| ------------- | ---------- | --------- | ------- |
| [API name]    | [Consumer] | [Purpose] | [Notes] |

### External Integrations

| Integration           | Purpose   | Risk Level            | Notes   |
| --------------------- | --------- | --------------------- | ------- |
| [Third-party service] | [Purpose] | [Low / Medium / High] | [Notes] |

### API Concerns

- [Authentication / authorization concern]
- [Rate limiting concern]
- [Versioning concern]
- [Error handling concern]

---

## 6. Scalability Review

### Expected Load

| Metric                   | Expected Value | Notes   |
| ------------------------ | -------------: | ------- |
| Daily active users       |        [Value] | [Notes] |
| Peak requests per second |        [Value] | [Notes] |
| Storage growth           |        [Value] | [Notes] |
| Background jobs per day  |        [Value] | [Notes] |

### Scaling Strategy

[Describe how the system scales horizontally, vertically, or through managed services.]

### Bottlenecks

| Bottleneck   | Impact   | Recommendation   |
| ------------ | -------- | ---------------- |
| [Bottleneck] | [Impact] | [Recommendation] |

---

## 7. Security Review

### Authentication

[Describe how users, admins, services, and external systems authenticate.]

### Authorization

[Describe permission checks, roles, ownership rules, and access boundaries.]

### Sensitive Data

| Data Type   | Protection Method                       | Notes   |
| ----------- | --------------------------------------- | ------- |
| [Data type] | [Encryption / access control / masking] | [Notes] |

### Security Risks

| Risk   | Severity                         | Recommendation   |
| ------ | -------------------------------- | ---------------- |
| [Risk] | [Low / Medium / High / Critical] | [Recommendation] |

---

## 8. Reliability and Availability Review

### Failure Scenarios

| Scenario               | Expected Behavior   | Mitigation   |
| ---------------------- | ------------------- | ------------ |
| [Service unavailable]  | [Expected behavior] | [Mitigation] |
| [Database failure]     | [Expected behavior] | [Mitigation] |
| [External API failure] | [Expected behavior] | [Mitigation] |

### Backup and Recovery

- **Backup strategy:** [Describe]
- **Recovery time objective:** [RTO]
- **Recovery point objective:** [RPO]

### Graceful Degradation

[Describe what parts of the app can continue working when non-critical services fail.]

---

## 9. Observability Review

### Logging

[Describe what logs are captured and how they are structured.]

### Metrics

Key metrics to monitor:

- [Metric 1]
- [Metric 2]
- [Metric 3]

### Alerts

| Alert        | Trigger     | Severity                         |
| ------------ | ----------- | -------------------------------- |
| [Alert name] | [Condition] | [Low / Medium / High / Critical] |

### Tracing

[Describe whether distributed tracing is needed and where it should be added.]

---

## 10. Performance Review

### Critical User Flows

| Flow     | Target Performance | Risk                  |
| -------- | ------------------ | --------------------- |
| [Flow 1] | [Target]           | [Low / Medium / High] |
| [Flow 2] | [Target]           | [Low / Medium / High] |

### Performance Risks

- [Risk 1]
- [Risk 2]
- [Risk 3]

### Recommendations

- [Recommendation 1]
- [Recommendation 2]
- [Recommendation 3]

---

## 11. Maintainability Review

### Code Organization

[Describe whether the architecture is easy to understand, test, and modify.]

### Service Boundaries

[Evaluate whether responsibilities are clearly separated.]

### Testing Strategy

| Test Type         | Purpose                            | Required?  |
| ----------------- | ---------------------------------- | ---------- |
| Unit tests        | Test small units of logic          | [Yes / No] |
| Integration tests | Test service/database/API behavior | [Yes / No] |
| End-to-end tests  | Test full user flows               | [Yes / No] |
| Load tests        | Test scalability and performance   | [Yes / No] |

---

## 12. Cost Review

### Main Cost Drivers

- [Compute]
- [Database]
- [Storage]
- [Bandwidth]
- [Third-party APIs]
- [Monitoring tools]

### Cost Risks

| Risk   | Impact   | Recommendation   |
| ------ | -------- | ---------------- |
| [Risk] | [Impact] | [Recommendation] |

---

## 13. Architecture Decisions

| Decision     | Status                           | Reason   | Tradeoff   |
| ------------ | -------------------------------- | -------- | ---------- |
| [Decision 1] | [Accepted / Rejected / Deferred] | [Reason] | [Tradeoff] |
| [Decision 2] | [Accepted / Rejected / Deferred] | [Reason] | [Tradeoff] |

---

## 14. Risk Summary

| Risk     | Severity                         | Likelihood            | Owner   | Recommendation   |
| -------- | -------------------------------- | --------------------- | ------- | ---------------- |
| [Risk 1] | [Low / Medium / High / Critical] | [Low / Medium / High] | [Owner] | [Recommendation] |
| [Risk 2] | [Low / Medium / High / Critical] | [Low / Medium / High] | [Owner] | [Recommendation] |

---

## 15. Required Changes Before Approval

### Must Fix

- [Required change 1]
- [Required change 2]
- [Required change 3]

### Should Fix

- [Recommended improvement 1]
- [Recommended improvement 2]
- [Recommended improvement 3]

### Nice to Have

- [Optional improvement 1]
- [Optional improvement 2]
- [Optional improvement 3]

---

## 16. Final Decision

**Decision:** [Approved / Approved with conditions / Needs revision / Rejected]

### Reasoning

[Explain why this decision was made.]

### Follow-Up Actions

| Action        | Owner   | Due Date |
| ------------- | ------- | -------- |
| [Action item] | [Owner] | [Date]   |
| [Action item] | [Owner] | [Date]   |

---

## 17. Appendix

### Related Documents

- [Product Requirements Document]
- [Technical Specification]
- [System Architecture Diagram]
- [API Documentation]
- [Database Schema]

### Open Questions

- [Question 1]
- [Question 2]
- [Question 3]
