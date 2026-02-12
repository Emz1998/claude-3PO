# Product Backlog

**Project:** Avaris
**Last Updated:** 2026-02-11

---

## Priority Legend

- 🔴 **Must have** — MVP doesn't ship without it
- 🟡 **Should have** — significantly improves MVP but not blocking
- 🟢 **Nice to have** — post-MVP or if time allows

## ID Conventions

| Prefix | Type            | Example | Scope               |
| ------ | --------------- | ------- | ------------------- |
| EP-NNN | Epic            | EP-001  | Backlog (permanent) |
| US-NNN | User Story      | US-001  | Backlog → Sprint    |
| TS-NNN | Technical Story | TS-001  | Backlog → Sprint    |
| BG-NNN | Bug             | BG-001  | Backlog → Sprint    |
| SK-NNN | Spike           | SK-001  | Backlog → Sprint    |
| T-NNN  | Task            | T-001   | Sprint only         |

- All IDs are global and sequential within their prefix
- IDs are permanent — they follow a story from backlog through sprint to completion

---

## Status Values

### Story Status

| Status      | Meaning                                        |
| ----------- | ---------------------------------------------- |
| Not started | In backlog, not yet pulled into a sprint       |
| In Sprint   | Currently in an active sprint (note which one) |
| Completed   | All tasks done, moved to Completed table       |
| Deferred    | Explicitly pushed to post-MVP or later         |

### Epic Status

| Status      | Meaning                                      |
| ----------- | -------------------------------------------- |
| Not started | No stories from this epic have been started  |
| In Progress | At least one story is In Sprint or Completed |
| Done        | All stories in the epic are Completed        |

## Epics Overview

| ID     | Epic                          | Priority | Stories | Status      |
| ------ | ----------------------------- | -------- | ------- | ----------- |
| EP-001 | XGBoost Prediction Model      | 🔴       | 5       | Not started |
| EP-002 | Auto-generated SEO Blog Posts | 🔴       | 5       | Not started |
| EP-003 | Public Performance Dashboard  | 🔴       | 6       | Not started |
| EP-004 | Automated Prediction Pipeline | 🔴       | 4       | Not started |
| EP-005 | Google AdSense Integration    | 🟡       | 2       | Not started |

## Epic Details

### EP-001: XGBoost Prediction Model

**Description:** ML prediction model that retrains nightly on NBA data and generates daily moneyline predictions with probability percentages.
**Priority:** 🔴
**Status:** Not started

| ID     | Type | Story                                                                                                                                 | Priority | Status      | Sprint | Notes                |
| ------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------- | ------ | -------------------- |
| SK-001 | SK   | Investigate which NBA stats features yield the best XGBoost accuracy to decide on the feature set for model v1                        | 🔴       | Not started |        | Independent          |
| SK-002 | SK   | Investigate whether predictions should be generated pre-market or post-line-release to decide on pipeline timing                      | 🔴       | Not started |        | Independent          |
| TS-001 | TS   | As a developer, I need to implement data ingestion from NBA Stats API via nba_api so that the model has fresh training data           | 🔴       | Not started |        | Independent          |
| TS-002 | TS   | As a developer, I need to implement feature engineering and XGBoost model training so that daily predictions are produced             | 🔴       | Not started |        | Needs SK-001, TS-001 |
| US-001 | US   | As a casual bettor, I want to see ML-generated predictions with probability percentages so that I can make informed betting decisions | 🔴       | Not started |        | Needs TS-002         |

---

### EP-002: Auto-generated SEO Blog Posts

**Description:** Daily prediction blog posts auto-generated from model output, published as SEO-optimized content with team matchups and probabilities.
**Priority:** 🔴
**Status:** Not started

| ID     | Type | Story                                                                                                                                         | Priority | Status      | Sprint | Notes                |
| ------ | ---- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------- | ------ | -------------------- |
| SK-003 | SK   | Investigate optimal blog post format for SEO in sports prediction content to decide on post template structure                                | 🟡       | Not started |        | Independent          |
| US-002 | US   | As a casual bettor, I want daily prediction blog posts with team matchups and probabilities so that I can quickly see today's picks           | 🔴       | Not started |        | Needs TS-004, TS-005 |
| US-003 | US   | As a serious bettor, I want to see matchup context and confidence levels in blog posts so that I can evaluate pick quality                    | 🟡       | Not started |        | Needs SK-003         |
| TS-004 | TS   | As a developer, I need to build a blog post content generator that creates SEO-optimized content from prediction data so that posts rank well | 🔴       | Not started |        | Needs EP-001 output  |
| TS-005 | TS   | As a developer, I need to implement Next.js SSG blog page templates with ISR and placeholder content so that the page structure is ready      | 🔴       | Not started |        | Independent          |

---

### EP-003: Public Performance Dashboard

**Description:** Live public dashboard showing win/loss record, ROI tracking, and historical prediction results so users can verify the model's accuracy.
**Priority:** 🔴
**Status:** Not started

| ID     | Type | Story                                                                                                                                    | Priority | Status      | Sprint | Notes                |
| ------ | ---- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------- | ------ | -------------------- |
| SK-004 | SK   | Investigate how to handle postponed or cancelled games in the performance dashboard to decide on edge case handling                      | 🟡       | Not started |        | Independent          |
| US-004 | US   | As a casual bettor, I want to see a public win/loss record with mock data so that I can verify the layout before live data               | 🔴       | Not started |        | Independent          |
| US-005 | US   | As a serious bettor, I want to see ROI tracking and historical results so that I can evaluate the model's profitability                  | 🔴       | Not started |        | Needs SK-004         |
| TS-017 | TS   | As a developer, I need to connect the dashboard to live prediction and results data from Firestore so that metrics are real              | 🔴       | Not started |        | Needs EP-001, EP-004 |
| TS-006 | TS   | As a developer, I need to implement the dashboard page layout with ISR and mock data so that the page structure is ready for live data   | 🔴       | Not started |        | Independent          |
| TS-007 | TS   | As a developer, I need to build data visualization components for win rate and ROI charts with mock datasets so that charts are reusable | 🟡       | Not started |        | Independent          |

---

### EP-004: Automated Prediction Pipeline

**Description:** End-to-end automation from data ingestion through prediction generation to content publication, running daily via GitHub Actions.
**Priority:** 🔴
**Status:** Not started

| ID     | Type | Story                                                                                                                                                 | Priority | Status      | Sprint | Notes                 |
| ------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------- | ------ | --------------------- |
| US-006 | US   | As a casual bettor, I want daily predictions published automatically every morning so that I can check picks before placing bets                      | 🔴       | Not started |        | Needs EP-001 pipeline |
| TS-008 | TS   | As a developer, I need to set up GitHub Actions cron workflows for daily pipeline automation so that predictions generate without manual intervention | 🔴       | Not started |        | Needs EP-001 scripts  |
| TS-009 | TS   | As a developer, I need to implement the results update pipeline that fetches game outcomes and updates Firestore so that performance data is accurate | 🔴       | Not started |        | Needs SK-002, TS-013  |
| TS-010 | TS   | As a developer, I need to implement pipeline failure alerting so that silent failures are caught immediately                                          | 🟡       | Not started |        | Needs TS-008          |

---

### EP-005: Google AdSense Integration

**Description:** Display ads integrated into blog posts and dashboard pages for revenue generation from day one.
**Priority:** 🟡
**Status:** Not started

| ID     | Type | Story                                                                                                                          | Priority | Status      | Sprint | Notes                     |
| ------ | ---- | ------------------------------------------------------------------------------------------------------------------------------ | -------- | ----------- | ------ | ------------------------- |
| US-007 | US   | As a casual bettor, I want non-intrusive ads that don't disrupt reading predictions so that my experience remains pleasant     | 🟡       | Not started |        | Needs EP-002/EP-003 pages |
| TS-011 | TS   | As a developer, I need to integrate Google AdSense with display ads on blog posts and dashboard so that the site earns revenue | 🟡       | Not started |        | Needs EP-002/EP-003 pages |

---

## Tech Debt / Infrastructure

| ID     | Type | Story                                                                                                                                                     | Priority | Status      | Sprint | Notes        |
| ------ | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------- | ------ | ------------ |
| TS-012 | TS   | As a developer, I need to set up Next.js 15 project scaffold with TypeScript strict mode, ESLint, and Prettier so that the web app has a solid foundation | 🔴       | Not started |        | Independent  |
| TS-013 | TS   | As a developer, I need to configure Firebase Firestore with collection schemas and security rules so that data is structured and secure                   | 🔴       | Not started |        | Independent  |
| TS-014 | TS   | As a developer, I need to set up Vitest for web testing and pytest for pipeline testing so that code quality is enforced                                  | 🔴       | Not started |        | Independent  |
| TS-015 | TS   | As a developer, I need to configure Vercel deployment with preview and production deployments so that CI/CD is automated                                  | 🟡       | Not started |        | Needs TS-012 |
| TS-016 | TS   | As a developer, I need to set up the Python pipeline project structure with dependencies and virtual environment so that ML development can begin         | 🔴       | Not started |        | Independent  |

---

## Bug Backlog

| ID  | Bug | Severity | Found In | Status | Sprint | Notes |
| --- | --- | -------- | -------- | ------ | ------ | ----- |

_No bugs reported yet._

---

## Completed

| ID  | Type | Epic | Story | Completed | Sprint |
| --- | ---- | ---- | ----- | --------- | ------ |
