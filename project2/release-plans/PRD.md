# Avaris - Product Requirements Document

## Overview

**Name:** Avaris - NBA Betting Analytics Platform

**Type:** web-application

**Elevator Pitch:** A transparent, data-driven NBA game prediction service powered by XGBoost machine learning, delivering daily picks with verifiable track records through an ad-supported blog that evolves into a premium subscription platform with automated prediction tools.

**Industry Problem:** Sports betting markets are saturated with tout services making questionable claims without transparent track records. Casual and serious bettors lack access to reliable, data-driven predictions with accountability. Existing prediction services hide their historical performance or cherry-pick winning streaks to mislead users.

**Solutions:**

- Build XGBoost machine learning model trained on NBA Stats API data to predict game outcomes
- Launch ad-supported blog with daily game predictions in SEO-optimized article format
- Display transparent performance dashboard showing win rate, ROI, and complete historical results
- Automate daily prediction pipeline using scheduled jobs to generate fresh picks each morning
- Transition to subscription model once proven performance threshold (55%+ win rate) is achieved
- Develop desktop prediction bot application for premium users to access predictions programmatically
- Provide tiered service serving both casual bettors (free moneyline picks) and serious bettors (premium spreads and totals)

**Goals:**

- Achieve 55%+ win rate over 100+ predictions to beat break-even threshold
- Build transparent track record through publicly displayed historical performance
- Launch MVP ad-supported blog with daily picks and performance dashboard
- Generate 5k+ monthly visitors through SEO and content marketing
- Reach $1k-5k monthly recurring revenue from ads and early subscribers within 12 months
- Develop subscription tiers with premium features (spreads, totals, API access)

## User Stories

### US-001: Fetch Current Season Team Stats

**As a** system, **I want to** fetch current season team statistics from NBA Stats API, **so that** the ML model has up-to-date data for predictions.

**Acceptance Criteria:**

- AC-001: Given the data pipeline is running, when a fetch job executes, then team statistics for the current season are retrieved and stored in Parquet format.
- AC-002: Given the NBA Stats API is rate-limited, when requests exceed limits, then the system implements exponential backoff and retries.

### US-002: Fetch Player Statistics

**As a** system, **I want to** fetch player-level statistics including injuries and rest days, **so that** predictions account for roster availability.

**Acceptance Criteria:**

- AC-003: Given the data pipeline runs, when player data is fetched, then key player stats (points, assists, rebounds, usage rate) are stored.
- AC-004: Given injury data is available, when player status changes, then the system updates injury flags within 24 hours.

### US-003: Store Historical Data

**As a** system, **I want to** store historical game data from past seasons, **so that** the ML model can be trained and backtested.

**Acceptance Criteria:**

- AC-005: Given historical data is requested, when the pipeline runs, then game results from 2022-23 and 2023-24 seasons are stored.
- AC-006: Given data is stored in Parquet files, when queried, then data retrieval completes in under 2 seconds for any query.

## Key Requirements

### Functional

- FR-001: System shall fetch team statistics including win rates, point differentials, offensive/defensive ratings from NBA Stats API.
- FR-002: System shall fetch player statistics including key metrics, injury reports, and rest days.
- FR-003: System shall store all data in Parquet file format for efficient querying.
- FR-004: System shall implement rate limiting and retry logic for API calls.

### Non-Functional

- NFR-001: Data pipeline shall complete daily refresh within 30 minutes.
- NFR-002: System shall handle API rate limits gracefully without data loss.

## Risks

- **R001: NBA Stats API Rate Limiting**
  - Overview: The NBA Stats API may impose strict rate limits that slow data collection.
  - Impact: Data freshness may be compromised, affecting prediction accuracy.
  - Probability: High
  - Mitigation: Implement caching, batch requests during off-peak hours, and store data locally to minimize API calls.

- **R002: API Schema Changes**
  - Overview: NBA Stats API may change response schemas without notice.
  - Impact: Data pipeline breaks, requiring immediate fixes.
  - Probability: Medium
  - Mitigation: Implement schema validation and alerting for unexpected response formats.

## Success Metrics

- SM-001: Data Pipeline Operational - Data pipeline successfully fetches and stores team and player data daily.
- SM-002: Historical Data Available - At least 2 full seasons of historical game data are stored and queryable.
- SM-003: Data Freshness Maintained - Data is updated within 24 hours of latest NBA games being played.

## Timeline

### Milestone 1 `(02/15/26)`

**EPIC-001:** Foundation - Environment Setup

### Milestone 2 `(02/22/26)`

**EPIC-002:** Core Features

- FEAT-001: NBA Data Pipeline Foundation
- FEAT-002: NBA Data Pipeline Foundation
- FEAT-003: NBA Data Pipeline Foundation

### Milestone 3 `(03/01/26)`

**EPIC-003:** Core Features

- FEAT-001: NBA Data Pipeline Foundation
- FEAT-002: NBA Data Pipeline Foundation
- FEAT-003: NBA Data Pipeline Foundation
