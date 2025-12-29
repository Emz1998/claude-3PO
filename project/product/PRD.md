# Avaris - Product Requirements Document

## Metadata

- **Current Version:** v0.1.0
- **Stable Version:** v1.0.0
- **Last Updated:** 2025-12-28
- **Updated By:** Claude AI

## ID Conventions

| Prefix | Entity                     | Example |
| ------ | -------------------------- | ------- |
| F      | Feature                    | F001    |
| US     | User Story                 | US-001  |
| AC     | Acceptance Criteria        | AC-001  |
| FR     | Functional Requirement     | FR-001  |
| NFR    | Non-Functional Requirement | NFR-001 |
| D      | Dependency                 | D001    |
| R      | Risk                       | R001    |
| SC     | Success Criteria           | SC-001  |

## Risk Probability

- **Low** - Unlikely to occur (<30% chance)
- **Medium** - Possible occurrence (30-60% chance)
- **High** - Likely to occur (>60% chance)

## Overview

- **Name:** Avaris - NBA Betting Analytics Platform
- **Type:** web-application
- **Elevator Pitch:** A transparent, data-driven NBA game prediction service powered by XGBoost machine learning, delivering daily picks with verifiable track records through an ad-supported blog that evolves into a premium subscription platform with automated prediction tools.
- **Industry Problem:** Sports betting markets are saturated with tout services making questionable claims without transparent track records. Casual and serious bettors lack access to reliable, data-driven predictions with accountability. Existing prediction services hide their historical performance or cherry-pick winning streaks to mislead users.
- **Solutions:**
    - Build XGBoost machine learning model trained on NBA Stats API data to predict game outcomes
  - Launch ad-supported blog with daily game predictions in SEO-optimized article format
  - Display transparent performance dashboard showing win rate, ROI, and complete historical results
  - Automate daily prediction pipeline using scheduled jobs to generate fresh picks each morning
  - Transition to subscription model once proven performance threshold (55%+ win rate) is achieved
  - Develop desktop prediction bot application for premium users to access predictions programmatically
  - Provide tiered service serving both casual bettors (free moneyline picks) and serious bettors (premium spreads and totals)
- **Goals:**
    - Achieve 55%+ win rate over 100+ predictions to beat break-even threshold
  - Build transparent track record through publicly displayed historical performance
  - Launch MVP ad-supported blog with daily picks and performance dashboard
  - Generate 5k+ monthly visitors through SEO and content marketing
  - Reach $1k-5k monthly recurring revenue from ads and early subscribers within 12 months
  - Develop subscription tiers with premium features (spreads, totals, API access)

## Tech Stack

- Next.js 14+
- React 19
- TypeScript
- Tailwind CSS v4
- Supabase
- Stripe
- Python 3.11+
- XGBoost
- Parquet
- GitHub Actions
- MDX
- Electron/Tauri

## Version: v0.1.0

- **Release Date:** 2025-01-15
- **Status:** not_started

### Feature: F001 - NBA Data Pipeline Foundation

**Description:** Establish core data infrastructure for fetching, storing, and managing NBA statistics from the NBA Stats API. This forms the foundation for all ML predictions.

**User Stories:**

- **US-001: Fetch Current Season Team Stats**

  - Story: As a system, I want to fetch current season team statistics from NBA Stats API, so that the ML model has up-to-date data for predictions.
  - Acceptance Criteria:
    - AC-001: Given the data pipeline is running, when a fetch job executes, then team statistics for the current season are retrieved and stored in Parquet format.
    - AC-002: Given the NBA Stats API is rate-limited, when requests exceed limits, then the system implements exponential backoff and retries.

- **US-002: Fetch Player Statistics**

  - Story: As a system, I want to fetch player-level statistics including injuries and rest days, so that predictions account for roster availability.
  - Acceptance Criteria:
    - AC-003: Given the data pipeline runs, when player data is fetched, then key player stats (points, assists, rebounds, usage rate) are stored.
    - AC-004: Given injury data is available, when player status changes, then the system updates injury flags within 24 hours.

- **US-003: Store Historical Data**

  - Story: As a system, I want to store historical game data from past seasons, so that the ML model can be trained and backtested.
  - Acceptance Criteria:
    - AC-005: Given historical data is requested, when the pipeline runs, then game results from 2022-23 and 2023-24 seasons are stored.
    - AC-006: Given data is stored in Parquet files, when queried, then data retrieval completes in under 2 seconds for any query.


**Requirements:**

_Functional:_

- FR-001: System shall fetch team statistics including win rates, point differentials, offensive/defensive ratings from NBA Stats API.
- FR-002: System shall fetch player statistics including key metrics, injury reports, and rest days.
- FR-003: System shall store all data in Parquet file format for efficient querying.
- FR-004: System shall implement rate limiting and retry logic for API calls.

_Non-Functional:_

- NFR-001: Data pipeline shall complete daily refresh within 30 minutes.
- NFR-002: System shall handle API rate limits gracefully without data loss.

**Dependencies:**

- D001: NBA Stats API - Assumption: API remains free and accessible with documented rate limits.
- D002: Python Runtime - Assumption: Python 3.11+ is available for data processing scripts.

**Risks:**

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


**Success Criteria:**

- SC-001: Data Pipeline Operational - Data pipeline successfully fetches and stores team and player data daily.
- SC-002: Historical Data Available - At least 2 full seasons of historical game data are stored and queryable.
- SC-003: Data Freshness Maintained - Data is updated within 24 hours of latest NBA games being played.

### Feature: F002 - XGBoost Model Training Infrastructure

**Description:** Build the machine learning infrastructure for training, evaluating, and versioning XGBoost models for game outcome prediction.

**User Stories:**

- **US-004: Train XGBoost Model**

  - Story: As a data scientist, I want to train an XGBoost model on historical NBA data, so that the system can predict game outcomes.
  - Acceptance Criteria:
    - AC-007: Given historical data is available, when training is initiated, then an XGBoost model is trained with specified hyperparameters.
    - AC-008: Given training completes, when the model is saved, then model artifacts and metadata are stored with version information.

- **US-005: Feature Engineering Pipeline**

  - Story: As a data scientist, I want automated feature engineering, so that raw data is transformed into predictive features.
  - Acceptance Criteria:
    - AC-009: Given raw game data, when feature engineering runs, then team performance metrics (L5, L10 form) are calculated.
    - AC-010: Given situational data, when features are generated, then home/away splits, back-to-back flags, and travel distance are computed.

- **US-006: Model Evaluation**

  - Story: As a data scientist, I want to evaluate model performance with cross-validation, so that I can assess prediction accuracy.
  - Acceptance Criteria:
    - AC-011: Given a trained model, when evaluation runs, then accuracy, log loss, and calibration metrics are computed.
    - AC-012: Given evaluation results, when metrics are reported, then win rate percentage is clearly displayed.


**Requirements:**

_Functional:_

- FR-005: System shall train XGBoost models using team performance, player stats, and situational features.
- FR-006: System shall generate features including recent form (L5, L10), home/away splits, and back-to-back indicators.
- FR-007: System shall evaluate models using time-series cross-validation.
- FR-008: System shall version and store trained models with metadata.

_Non-Functional:_

- NFR-003: Model training shall complete within 10 minutes on standard hardware.
- NFR-004: Feature engineering shall process a full season of data in under 5 minutes.

**Dependencies:**

- D003: XGBoost Library - Assumption: XGBoost Python library is stable and maintained.
- D004: F001 - NBA Data Pipeline - Assumption: Data pipeline provides clean, structured data for training.

**Risks:**

- **R003: Model Overfitting**

  - Overview: Model may overfit to historical patterns that do not generalize.
  - Impact: Poor prediction accuracy on new games.
  - Probability: Medium
  - Mitigation: Use time-series cross-validation and regularization parameters.

- **R004: Insufficient Predictive Signal**

  - Overview: Available features may not provide enough signal to beat 55% accuracy.
  - Impact: Product cannot launch if accuracy threshold is not met.
  - Probability: Medium
  - Mitigation: Iterate on feature engineering and explore additional data sources.


**Success Criteria:**

- SC-004: Model Training Functional - XGBoost model trains successfully on historical data.
- SC-005: Feature Pipeline Complete - All planned feature categories are implemented and tested.
- SC-006: Evaluation Metrics Available - Model evaluation produces accuracy, log loss, and calibration metrics.


## Version: v0.2.0

- **Release Date:** 2025-02-01
- **Status:** not_started

### Feature: F003 - Model Backtesting Framework

**Description:** Implement comprehensive backtesting to validate model performance on historical seasons before live deployment.

**User Stories:**

- **US-007: Backtest on Historical Seasons**

  - Story: As a data scientist, I want to backtest the model on 2022-23 and 2023-24 seasons, so that I can validate it does not overfit.
  - Acceptance Criteria:
    - AC-013: Given trained model, when backtesting runs, then predictions are generated for each game in test seasons.
    - AC-014: Given backtest results, when analysis completes, then win rate, ROI, and maximum drawdown are calculated.

- **US-008: Generate Backtest Reports**

  - Story: As a product owner, I want detailed backtest reports, so that I can assess readiness for launch.
  - Acceptance Criteria:
    - AC-015: Given backtest completes, when report is generated, then monthly performance breakdown is included.
    - AC-016: Given backtest report, when reviewed, then confidence intervals for win rate are displayed.


**Requirements:**

_Functional:_

- FR-009: System shall simulate predictions on historical seasons without data leakage.
- FR-010: System shall calculate ROI assuming standard -110 betting odds.
- FR-011: System shall generate monthly and seasonal performance reports.

_Non-Functional:_

- NFR-005: Backtesting a full season shall complete within 5 minutes.

**Dependencies:**

- D005: F002 - XGBoost Model - Assumption: Trained model is available for backtesting.

**Risks:**

- **R005: Data Leakage in Backtesting**

  - Overview: Improper backtesting may use future information, inflating results.
  - Impact: False confidence in model performance.
  - Probability: Medium
  - Mitigation: Implement strict temporal splits and code review for data leakage.


**Success Criteria:**

- SC-007: Backtest Validation Complete - Model achieves 55%+ win rate on held-out historical seasons.
- SC-008: No Data Leakage Detected - Code review confirms no future data is used in predictions.

### Feature: F004 - Paper Trading System

**Description:** Run live predictions without publishing to validate model performance on current season before public launch.

**User Stories:**

- **US-009: Generate Daily Paper Predictions**

  - Story: As a system, I want to generate predictions for today's games, so that performance can be tracked privately.
  - Acceptance Criteria:
    - AC-017: Given games are scheduled for today, when prediction job runs, then predictions are generated and stored.
    - AC-018: Given predictions exist, when games complete, then actual results are recorded and accuracy updated.

- **US-010: Track Paper Trading Performance**

  - Story: As a product owner, I want to track paper trading performance over time, so that I can decide when to launch publicly.
  - Acceptance Criteria:
    - AC-019: Given paper trading data, when dashboard is viewed, then cumulative win rate and ROI are displayed.
    - AC-020: Given 50+ predictions, when analysis runs, then statistical confidence in win rate is calculated.


**Requirements:**

_Functional:_

- FR-012: System shall generate predictions for all games each day automatically.
- FR-013: System shall record prediction results after games complete.
- FR-014: System shall provide paper trading dashboard showing running performance.

_Non-Functional:_

- NFR-006: Daily predictions shall be generated by 10 AM ET before lines move significantly.

**Dependencies:**

- D006: F001 - NBA Data Pipeline - Assumption: Fresh data is available for daily predictions.
- D007: F002 - XGBoost Model - Assumption: Trained model is deployed for inference.

**Risks:**

- **R006: Paper vs Live Performance Gap**

  - Overview: Paper trading may not reflect real-world conditions.
  - Impact: Live performance may differ from paper results.
  - Probability: Low
  - Mitigation: Paper trade for extended period (4+ weeks) before launch.


**Success Criteria:**

- SC-009: Paper Trading Operational - System generates and tracks predictions daily without manual intervention.
- SC-010: Launch Threshold Met - Paper trading achieves 55%+ win rate over 50+ predictions.


## Version: v0.3.0

- **Release Date:** 2025-02-15
- **Status:** not_started

### Feature: F005 - Next.js Blog Foundation

**Description:** Build the core Next.js application infrastructure for the prediction blog, including routing, layouts, and basic pages.

**User Stories:**

- **US-011: View Homepage with Today's Picks**

  - Story: As a visitor, I want to see today's picks prominently on the homepage, so that I can quickly access current predictions.
  - Acceptance Criteria:
    - AC-021: Given I visit the homepage, when the page loads, then today's game predictions are displayed with probability percentages.
    - AC-022: Given no games are scheduled today, when I visit the homepage, then a message indicates no games and shows next game date.

- **US-012: Navigate Blog Structure**

  - Story: As a visitor, I want clear navigation to browse predictions by date, so that I can find historical picks.
  - Acceptance Criteria:
    - AC-023: Given I am on any page, when I use the navigation, then I can access homepage, archives, and about sections.
    - AC-024: Given I visit the archives, when I select a date, then predictions for that date are displayed.


**Requirements:**

_Functional:_

- FR-015: System shall display today's predictions on the homepage with team names and probability percentages.
- FR-016: System shall provide navigation to homepage, archives, and about pages.
- FR-017: System shall support responsive design for desktop and mobile viewing.

_Non-Functional:_

- NFR-007: Homepage shall load in under 2 seconds on desktop connections.
- NFR-008: Site shall achieve 90+ Lighthouse performance score.

**Dependencies:**

- D008: Next.js Framework - Assumption: Next.js 14+ with App Router is used.
- D009: React 19 - Assumption: React 19 stable release is available.
- D010: Tailwind CSS v4 - Assumption: Tailwind v4 is stable and documented.

**Risks:**

- **R007: Framework Version Instability**

  - Overview: New versions of Next.js, React 19, or Tailwind v4 may have bugs.
  - Impact: Development delays due to framework issues.
  - Probability: Low
  - Mitigation: Pin versions and monitor release notes for breaking changes.


**Success Criteria:**

- SC-011: Homepage Functional - Homepage displays today's picks with proper formatting.
- SC-012: Navigation Complete - All core navigation links are functional.
- SC-013: Performance Target Met - Lighthouse performance score is 90+.


## Version: v0.4.0

- **Release Date:** 2025-03-01
- **Status:** not_started

### Feature: F006 - MDX Daily Picks Pages

**Description:** Implement SEO-optimized daily prediction pages using MDX format for automated content generation.

**User Stories:**

- **US-013: View Game Prediction Page**

  - Story: As a visitor, I want to view detailed prediction pages for each game, so that I can understand the analysis behind picks.
  - Acceptance Criteria:
    - AC-025: Given a game prediction page exists, when I visit the URL, then team matchup, prediction, and probability are displayed.
    - AC-026: Given the page loads, when I scroll, then key factors influencing the prediction are shown.

- **US-014: Find Predictions via Search Engines**

  - Story: As a potential user, I want to find prediction pages through search engines, so that I discover the service organically.
  - Acceptance Criteria:
    - AC-027: Given prediction pages are published, when indexed by search engines, then pages appear for '[Team A] vs [Team B] prediction' queries.
    - AC-028: Given a prediction page, when viewed, then proper meta tags (title, description, Open Graph) are present.


**Requirements:**

_Functional:_

- FR-018: System shall generate MDX files for each daily prediction automatically.
- FR-019: Prediction pages shall include team matchup, prediction pick, probability percentage, and key factors.
- FR-020: Pages shall have SEO-optimized URLs in format /predictions/[date]/[team-a]-vs-[team-b].
- FR-021: Pages shall include proper meta tags for search engine and social media optimization.

_Non-Functional:_

- NFR-009: MDX generation shall complete within 5 minutes for all daily games.
- NFR-010: Generated pages shall pass Google Search Console validation.

**Dependencies:**

- D011: F005 - Next.js Blog Foundation - Assumption: Blog infrastructure is ready for MDX integration.
- D012: F004 - Paper Trading System - Assumption: Daily predictions are generated and available.

**Risks:**

- **R008: SEO Ranking Competition**

  - Overview: Established sports betting sites dominate search rankings.
  - Impact: Organic traffic growth may be slower than expected.
  - Probability: High
  - Mitigation: Focus on long-tail keywords and unique value proposition (transparent track record).


**Success Criteria:**

- SC-014: MDX Generation Automated - Daily prediction pages are auto-generated without manual intervention.
- SC-015: Pages SEO Optimized - All pages pass SEO audit with proper meta tags and structured data.

### Feature: F007 - Performance Dashboard

**Description:** Public-facing dashboard displaying historical prediction performance including win rate, ROI, and recent results.

**User Stories:**

- **US-015: View Overall Performance**

  - Story: As a visitor, I want to see overall prediction performance metrics, so that I can evaluate the service's track record.
  - Acceptance Criteria:
    - AC-029: Given I visit the performance dashboard, when the page loads, then overall win rate and total predictions are displayed.
    - AC-030: Given performance data exists, when displayed, then ROI percentage assuming standard betting is shown.

- **US-016: View Recent Results**

  - Story: As a visitor, I want to see recent prediction results, so that I can verify current performance.
  - Acceptance Criteria:
    - AC-031: Given recent predictions exist, when I view the dashboard, then last 10 predictions with outcomes are displayed.
    - AC-032: Given a prediction result, when displayed, then team names, pick, and win/loss indicator are shown.

- **US-017: View Monthly Breakdown**

  - Story: As a visitor, I want to see monthly performance breakdown, so that I can assess consistency.
  - Acceptance Criteria:
    - AC-033: Given multiple months of data exist, when I view monthly breakdown, then win rate per month is displayed.
    - AC-034: Given monthly data, when displayed, then trends are visualized (chart or graph).


**Requirements:**

_Functional:_

- FR-022: Dashboard shall display overall win rate, total predictions, and ROI.
- FR-023: Dashboard shall show last 10 prediction results with outcomes.
- FR-024: Dashboard shall provide monthly performance breakdown.
- FR-025: Dashboard shall visualize performance trends over time.

_Non-Functional:_

- NFR-011: Dashboard shall update within 1 hour of game completion.
- NFR-012: Dashboard shall load in under 3 seconds.

**Dependencies:**

- D013: F004 - Paper Trading System - Assumption: Historical prediction data is available for display.
- D014: F005 - Next.js Blog Foundation - Assumption: Blog infrastructure supports dashboard pages.

**Risks:**

- **R009: Performance Below Expectations**

  - Overview: Public dashboard may show poor performance during bad streaks.
  - Impact: Trust and credibility damaged during losing periods.
  - Probability: Medium
  - Mitigation: Emphasize long-term performance and statistical variance in dashboard copy.


**Success Criteria:**

- SC-016: Dashboard Displays Metrics - All required performance metrics are visible and accurate.
- SC-017: Data Updates Automatically - Dashboard reflects latest results within 1 hour of game completion.
- SC-018: Performance Load Time Met - Dashboard loads within 3 seconds.


## Version: v0.5.0

- **Release Date:** 2025-03-15
- **Status:** not_started

### Feature: F008 - Automated Prediction Pipeline

**Description:** Implement end-to-end automation for daily predictions using scheduled jobs (cron/GitHub Actions).

**User Stories:**

- **US-018: Automatic Daily Predictions**

  - Story: As a system operator, I want predictions generated automatically each morning, so that no manual intervention is required.
  - Acceptance Criteria:
    - AC-035: Given it is a game day, when the scheduled job runs, then predictions are generated for all games.
    - AC-036: Given predictions are generated, when the job completes, then MDX files are created and committed to repository.

- **US-019: Automatic Result Recording**

  - Story: As a system, I want game results recorded automatically, so that performance tracking stays current.
  - Acceptance Criteria:
    - AC-037: Given games have completed, when the results job runs, then outcomes are fetched and recorded.
    - AC-038: Given results are recorded, when dashboard data updates, then win/loss status is accurate.

- **US-020: Pipeline Failure Alerting**

  - Story: As a system operator, I want to be alerted if the pipeline fails, so that issues can be addressed quickly.
  - Acceptance Criteria:
    - AC-039: Given a pipeline step fails, when failure is detected, then an email or Slack notification is sent.
    - AC-040: Given an alert is sent, when reviewed, then error details and failing step are included.


**Requirements:**

_Functional:_

- FR-026: System shall run prediction pipeline daily at 8 AM ET via scheduled job.
- FR-027: System shall automatically commit generated MDX files to repository.
- FR-028: System shall fetch and record game results daily after games complete.
- FR-029: System shall send alerts on pipeline failures via email or Slack.

_Non-Functional:_

- NFR-013: Pipeline shall complete within 30 minutes of scheduled start time.
- NFR-014: Pipeline shall achieve 99% uptime over 30-day rolling period.

**Dependencies:**

- D015: GitHub Actions - Assumption: GitHub Actions is available for scheduling and execution.
- D016: F001, F002, F006 - Assumption: Data pipeline, model, and MDX generation are functional.

**Risks:**

- **R010: Pipeline Reliability**

  - Overview: External dependencies (API, GitHub Actions) may cause failures.
  - Impact: Predictions not published, damaging user trust.
  - Probability: Medium
  - Mitigation: Implement retries, fallback mechanisms, and comprehensive alerting.


**Success Criteria:**

- SC-019: Pipeline Runs Daily - Automated pipeline executes daily without manual intervention.
- SC-020: Alerts Functional - Failure alerts are received within 5 minutes of pipeline error.
- SC-021: Uptime Target Met - Pipeline achieves 99% uptime over first 30 days.


## Version: v0.6.0

- **Release Date:** 2025-04-01
- **Status:** not_started

### Feature: F009 - Google AdSense Integration

**Description:** Integrate Google AdSense for ad monetization on the blog.

**User Stories:**

- **US-021: Display Ads on Pages**

  - Story: As a site owner, I want ads displayed on blog pages, so that the site generates ad revenue.
  - Acceptance Criteria:
    - AC-041: Given AdSense is integrated, when a visitor loads a page, then ads are displayed in designated slots.
    - AC-042: Given ads are displayed, when viewed, then ads do not obstruct primary content.

- **US-022: Non-Intrusive Ad Placement**

  - Story: As a visitor, I want ads that do not interfere with content consumption, so that my experience is not degraded.
  - Acceptance Criteria:
    - AC-043: Given ads are displayed, when I read prediction content, then ads are placed in sidebar or between sections.
    - AC-044: Given I am on mobile, when viewing the page, then ads are appropriately sized and positioned.


**Requirements:**

_Functional:_

- FR-030: System shall integrate Google AdSense code on all blog pages.
- FR-031: Ad placements shall be in sidebar and between content sections.
- FR-032: System shall support responsive ad units for mobile and desktop.

_Non-Functional:_

- NFR-015: Ad loading shall not increase page load time by more than 500ms.
- NFR-016: Ads shall comply with Google AdSense policies.

**Dependencies:**

- D017: Google AdSense Account - Assumption: AdSense account is approved and active.
- D018: F005 - Next.js Blog Foundation - Assumption: Blog pages are ready for ad integration.

**Risks:**

- **R011: AdSense Approval Delay**

  - Overview: Google AdSense approval may take time or be rejected.
  - Impact: Monetization delayed, affecting revenue targets.
  - Probability: Medium
  - Mitigation: Submit for approval early; have alternative ad networks as backup.

- **R012: Low Ad Revenue Initially**

  - Overview: Low traffic means low ad revenue at launch.
  - Impact: Revenue targets may not be met initially.
  - Probability: High
  - Mitigation: Focus on traffic growth through SEO and content marketing.


**Success Criteria:**

- SC-022: Ads Displaying Correctly - Ads appear on all blog pages without layout issues.
- SC-023: AdSense Approved - Google AdSense account is approved and generating impressions.
- SC-024: Performance Impact Minimal - Page load time increase is under 500ms with ads.

### Feature: F010 - MVP Public Launch

**Description:** Official public launch of the ad-supported prediction blog after achieving performance threshold.

**User Stories:**

- **US-023: Access Public Blog**

  - Story: As a visitor, I want to access the publicly available prediction blog, so that I can use the service.
  - Acceptance Criteria:
    - AC-045: Given the site is launched, when I visit the URL, then the homepage loads with today's picks.
    - AC-046: Given I am a search engine user, when I search for predictions, then relevant pages may appear in results.

- **US-024: Trust Through Transparency**

  - Story: As a visitor, I want to see the full track record including losses, so that I can trust the service is honest.
  - Acceptance Criteria:
    - AC-047: Given I visit the performance dashboard, when viewing results, then all predictions including losses are displayed.
    - AC-048: Given the track record, when reviewed, then no cherry-picking or hidden results are evident.


**Requirements:**

_Functional:_

- FR-033: Site shall be deployed to production hosting environment.
- FR-034: All core features (homepage, predictions, dashboard) shall be functional.
- FR-035: Site shall have proper domain and SSL certificate.

_Non-Functional:_

- NFR-017: Site shall achieve 99.5% uptime.
- NFR-018: Site shall handle at least 1000 concurrent visitors.

**Dependencies:**

- D019: F005-F009 - Assumption: All MVP features are complete and tested.
- D020: Domain and Hosting - Assumption: Domain is registered and hosting provider selected.

**Risks:**

- **R013: Launch Performance Issues**

  - Overview: Unexpected traffic or bugs may cause issues at launch.
  - Impact: Poor first impression, user loss.
  - Probability: Medium
  - Mitigation: Soft launch to limited audience first; monitor closely.


**Success Criteria:**

- SC-025: Site Live and Accessible - Site is publicly accessible at production domain.
- SC-026: Core Features Functional - All MVP features work correctly in production.
- SC-027: Performance Threshold Met - Model has achieved 55%+ win rate over 50+ predictions before launch.


## Version: v0.7.0

- **Release Date:** 2025-05-01
- **Status:** not_started

### Feature: F011 - Email Newsletter System

**Description:** Build email capture and daily newsletter delivery for owned audience building.

**User Stories:**

- **US-025: Subscribe to Newsletter**

  - Story: As a visitor, I want to subscribe to the daily picks newsletter, so that I receive predictions in my inbox.
  - Acceptance Criteria:
    - AC-049: Given I am on the homepage, when I enter my email and submit, then I am subscribed to the newsletter.
    - AC-050: Given I subscribe, when confirmation is sent, then I receive a welcome email.

- **US-026: Receive Daily Picks Email**

  - Story: As a subscriber, I want to receive daily picks via email, so that I don't have to visit the site.
  - Acceptance Criteria:
    - AC-051: Given I am subscribed, when picks are published, then I receive an email with today's predictions.
    - AC-052: Given the email is received, when I read it, then team matchups and predictions are clearly formatted.

- **US-027: Unsubscribe from Newsletter**

  - Story: As a subscriber, I want to easily unsubscribe, so that I can stop receiving emails.
  - Acceptance Criteria:
    - AC-053: Given I receive a newsletter email, when I click unsubscribe, then I am removed from the list.
    - AC-054: Given I unsubscribe, when confirmed, then I no longer receive newsletter emails.


**Requirements:**

_Functional:_

- FR-036: System shall provide email subscription form on homepage and prediction pages.
- FR-037: System shall send daily newsletter with predictions each morning.
- FR-038: System shall support double opt-in for subscriptions.
- FR-039: System shall include one-click unsubscribe in all emails.

_Non-Functional:_

- NFR-019: Newsletter delivery shall complete within 1 hour of predictions being published.
- NFR-020: Email deliverability shall exceed 95%.

**Dependencies:**

- D021: Email Service Provider - Assumption: Email service (e.g., Resend, SendGrid) is configured.
- D022: F008 - Automated Pipeline - Assumption: Daily predictions trigger newsletter sending.

**Risks:**

- **R014: Email Deliverability Issues**

  - Overview: Emails may be marked as spam or not delivered.
  - Impact: Subscriber engagement drops.
  - Probability: Medium
  - Mitigation: Use reputable ESP, implement SPF/DKIM, warm up sending domain.


**Success Criteria:**

- SC-028: Subscription Functional - Users can successfully subscribe and receive welcome email.
- SC-029: Daily Newsletter Delivered - Newsletter is sent daily with predictions to all subscribers.
- SC-030: Deliverability Target Met - Email deliverability exceeds 95%.

### Feature: F012 - Social Media Integration

**Description:** Add social sharing capabilities and automated posting to Twitter/X for audience growth.

**User Stories:**

- **US-028: Share Predictions on Social**

  - Story: As a visitor, I want to share predictions on social media, so that I can discuss with friends.
  - Acceptance Criteria:
    - AC-055: Given I am on a prediction page, when I click share, then I can share to Twitter/X with pre-filled text.
    - AC-056: Given I share to social media, when the post is created, then it includes a link back to the prediction page.

- **US-029: Auto-Post Daily Picks**

  - Story: As a site owner, I want daily picks auto-posted to Twitter/X, so that social followers are notified.
  - Acceptance Criteria:
    - AC-057: Given predictions are published, when the pipeline completes, then a summary tweet is posted.
    - AC-058: Given a tweet is posted, when viewed, then it includes game count and link to homepage.


**Requirements:**

_Functional:_

- FR-040: Prediction pages shall include social share buttons for Twitter/X.
- FR-041: System shall auto-post daily picks summary to Twitter/X.
- FR-042: Social posts shall use Open Graph meta tags for rich previews.

_Non-Functional:_

- NFR-021: Auto-posts shall occur within 15 minutes of predictions being published.

**Dependencies:**

- D023: Twitter/X API Access - Assumption: Twitter/X developer account with posting permissions.

**Risks:**

- **R015: Twitter API Changes**

  - Overview: Twitter/X API pricing or access may change.
  - Impact: Auto-posting feature may break or become expensive.
  - Probability: Medium
  - Mitigation: Design for manual fallback; monitor API status.


**Success Criteria:**

- SC-031: Share Buttons Functional - Social share buttons work correctly on all prediction pages.
- SC-032: Auto-Posting Active - Daily picks are automatically posted to Twitter/X.


## Version: v0.8.0

- **Release Date:** 2025-06-01
- **Status:** not_started

### Feature: F013 - Supabase User Authentication

**Description:** Implement user authentication using Supabase for future premium features.

**User Stories:**

- **US-030: Create User Account**

  - Story: As a visitor, I want to create an account, so that I can access member features in the future.
  - Acceptance Criteria:
    - AC-059: Given I am on the signup page, when I submit email and password, then my account is created.
    - AC-060: Given I sign up, when account is created, then I receive a verification email.

- **US-031: Login to Account**

  - Story: As a registered user, I want to log in, so that I can access my account.
  - Acceptance Criteria:
    - AC-061: Given I have an account, when I enter valid credentials, then I am logged in.
    - AC-062: Given I am logged in, when I view the site, then my logged-in status is indicated.

- **US-032: Password Reset**

  - Story: As a user, I want to reset my password if forgotten, so that I can regain account access.
  - Acceptance Criteria:
    - AC-063: Given I forgot my password, when I request reset, then I receive a reset email.
    - AC-064: Given I receive reset email, when I set new password, then I can log in with new password.


**Requirements:**

_Functional:_

- FR-043: System shall support email/password authentication via Supabase.
- FR-044: System shall require email verification for new accounts.
- FR-045: System shall support password reset via email.
- FR-046: System shall maintain secure session management.

_Non-Functional:_

- NFR-022: Authentication flows shall complete in under 3 seconds.
- NFR-023: Password storage shall use bcrypt with appropriate cost factor.

**Dependencies:**

- D024: Supabase - Assumption: Supabase project is configured with auth enabled.

**Risks:**

- **R016: Authentication Security**

  - Overview: Security vulnerabilities in auth implementation.
  - Impact: User accounts compromised.
  - Probability: Low
  - Mitigation: Use Supabase built-in auth; follow security best practices.


**Success Criteria:**

- SC-033: Registration Functional - Users can successfully create and verify accounts.
- SC-034: Login Functional - Users can log in and out successfully.
- SC-035: Password Reset Works - Users can reset passwords via email.

### Feature: F014 - User Profile Management

**Description:** Allow users to manage their profile and preferences.

**User Stories:**

- **US-033: View Profile**

  - Story: As a logged-in user, I want to view my profile, so that I can see my account information.
  - Acceptance Criteria:
    - AC-065: Given I am logged in, when I visit my profile, then I see my email and account creation date.

- **US-034: Update Email Preferences**

  - Story: As a user, I want to manage email preferences, so that I control what emails I receive.
  - Acceptance Criteria:
    - AC-066: Given I am on profile settings, when I toggle newsletter preference, then my preference is saved.
    - AC-067: Given I opt out of newsletter, when next newsletter sends, then I do not receive it.


**Requirements:**

_Functional:_

- FR-047: System shall provide user profile page showing account details.
- FR-048: System shall allow users to update email notification preferences.

_Non-Functional:_

- NFR-024: Profile page shall load in under 2 seconds.

**Dependencies:**

- D025: F013 - User Authentication - Assumption: Authentication system is functional.

**Risks:**

- None

**Success Criteria:**

- SC-036: Profile Page Accessible - Logged-in users can view their profile.
- SC-037: Preferences Saveable - Email preferences can be updated and are respected.


## Version: v0.9.0

- **Release Date:** 2025-07-01
- **Status:** not_started

### Feature: F015 - Stripe Payment Integration

**Description:** Integrate Stripe for subscription payment processing.

**User Stories:**

- **US-035: Subscribe to Premium**

  - Story: As a user, I want to subscribe to premium tier, so that I can access advanced predictions.
  - Acceptance Criteria:
    - AC-068: Given I am logged in, when I select premium subscription, then I am directed to Stripe checkout.
    - AC-069: Given I complete payment, when checkout succeeds, then my account is upgraded to premium.

- **US-036: Manage Subscription**

  - Story: As a subscriber, I want to manage my subscription, so that I can cancel or change plans.
  - Acceptance Criteria:
    - AC-070: Given I am a premium user, when I visit subscription settings, then I can view my plan details.
    - AC-071: Given I want to cancel, when I initiate cancellation, then my subscription is cancelled at period end.

- **US-037: View Payment History**

  - Story: As a subscriber, I want to see payment history, so that I can track my spending.
  - Acceptance Criteria:
    - AC-072: Given I am subscribed, when I view payment history, then past invoices are displayed.


**Requirements:**

_Functional:_

- FR-049: System shall integrate Stripe for subscription payments.
- FR-050: System shall support monthly subscription billing.
- FR-051: System shall provide subscription management portal.
- FR-052: System shall handle webhook events for subscription lifecycle.

_Non-Functional:_

- NFR-025: Payment processing shall be PCI compliant via Stripe.
- NFR-026: Subscription status updates shall occur within 5 minutes of payment events.

**Dependencies:**

- D026: Stripe Account - Assumption: Stripe account is verified and products configured.
- D027: F013 - User Authentication - Assumption: Users are authenticated before subscribing.

**Risks:**

- **R017: Payment Failures**

  - Overview: Users may experience payment failures.
  - Impact: Lost revenue and frustrated users.
  - Probability: Low
  - Mitigation: Implement retry logic and clear error messaging.


**Success Criteria:**

- SC-038: Checkout Functional - Users can complete subscription checkout via Stripe.
- SC-039: Subscription Status Accurate - User subscription status updates correctly after payment.
- SC-040: Cancellation Works - Users can cancel subscriptions through the portal.

### Feature: F016 - Premium Spread and Totals Predictions

**Description:** Add spread and totals predictions as premium-only features.

**User Stories:**

- **US-038: View Spread Predictions**

  - Story: As a premium user, I want to see spread predictions, so that I can bet against the spread.
  - Acceptance Criteria:
    - AC-073: Given I am premium, when I view a prediction, then spread prediction is displayed.
    - AC-074: Given I am free user, when I view a prediction, then spread prediction is locked/blurred.

- **US-039: View Totals Predictions**

  - Story: As a premium user, I want to see over/under predictions, so that I can bet on totals.
  - Acceptance Criteria:
    - AC-075: Given I am premium, when I view a prediction, then over/under prediction is displayed.
    - AC-076: Given I am free user, when I view a prediction, then totals prediction is locked/blurred.


**Requirements:**

_Functional:_

- FR-053: System shall generate spread predictions using enhanced model.
- FR-054: System shall generate over/under predictions for game totals.
- FR-055: System shall gate spread and totals predictions behind premium subscription.

_Non-Functional:_

- NFR-027: Premium predictions shall be generated alongside moneyline predictions.

**Dependencies:**

- D028: F002 - XGBoost Model - Assumption: Model can be extended for spread and totals predictions.
- D029: F015 - Stripe Integration - Assumption: Subscription status determines feature access.

**Risks:**

- **R018: Spread Model Accuracy**

  - Overview: Spread predictions may not achieve same accuracy as moneyline.
  - Impact: Premium value proposition weakened.
  - Probability: Medium
  - Mitigation: Backtest thoroughly before launch; be transparent about different accuracy.


**Success Criteria:**

- SC-041: Spread Predictions Generated - Spread predictions are generated daily for premium users.
- SC-042: Totals Predictions Generated - Over/under predictions are generated daily for premium users.
- SC-043: Feature Gating Works - Free users cannot access premium predictions.


## Version: v0.10.0

- **Release Date:** 2025-08-01
- **Status:** not_started

### Feature: F017 - Prediction API for Premium Users

**Description:** Provide API access for power users to retrieve predictions programmatically.

**User Stories:**

- **US-040: Generate API Key**

  - Story: As a premium user, I want to generate an API key, so that I can access predictions programmatically.
  - Acceptance Criteria:
    - AC-077: Given I am premium, when I visit API settings, then I can generate an API key.
    - AC-078: Given I generate a key, when displayed, then I can copy it to clipboard.

- **US-041: Fetch Predictions via API**

  - Story: As a developer, I want to fetch predictions via API, so that I can integrate with my tools.
  - Acceptance Criteria:
    - AC-079: Given I have an API key, when I call /api/predictions, then I receive today's predictions in JSON.
    - AC-080: Given I call the API, when response returns, then it includes moneyline, spread, and totals predictions.

- **US-042: API Rate Limiting**

  - Story: As a system, I want to rate limit API requests, so that resources are not abused.
  - Acceptance Criteria:
    - AC-081: Given a user makes many requests, when rate limit exceeded, then 429 response is returned.
    - AC-082: Given rate limit is enforced, when user waits, then requests succeed again.


**Requirements:**

_Functional:_

- FR-056: System shall allow premium users to generate API keys.
- FR-057: API shall return predictions in JSON format.
- FR-058: API shall include all prediction types (moneyline, spread, totals).
- FR-059: API shall enforce rate limits per user.

_Non-Functional:_

- NFR-028: API response time shall be under 500ms.
- NFR-029: Rate limit shall be 100 requests per hour per user.

**Dependencies:**

- D030: F015 - Stripe Integration - Assumption: Premium status determines API access.
- D031: F016 - Premium Predictions - Assumption: All prediction types are available.

**Risks:**

- **R019: API Abuse**

  - Overview: Users may share API keys or exceed intended usage.
  - Impact: Server resources strained.
  - Probability: Medium
  - Mitigation: Implement rate limiting and key rotation capabilities.


**Success Criteria:**

- SC-044: API Key Generation Works - Premium users can generate and manage API keys.
- SC-045: API Returns Predictions - API endpoint returns predictions in correct JSON format.
- SC-046: Rate Limiting Enforced - Excessive requests are rate limited with appropriate response.

### Feature: F018 - Early Access Predictions

**Description:** Provide premium users with early access to predictions before public release.

**User Stories:**

- **US-043: View Early Predictions**

  - Story: As a premium user, I want early access to predictions, so that I can bet before lines move.
  - Acceptance Criteria:
    - AC-083: Given I am premium, when predictions are generated, then I see them 2 hours before free users.
    - AC-084: Given early access period, when I view predictions, then 'Early Access' badge is displayed.

- **US-044: Email Early Predictions**

  - Story: As a premium subscriber, I want early predictions emailed, so that I'm notified immediately.
  - Acceptance Criteria:
    - AC-085: Given I am premium with newsletter enabled, when predictions generate, then I receive email 2 hours before free users.


**Requirements:**

_Functional:_

- FR-060: System shall release predictions to premium users 2 hours before free users.
- FR-061: System shall mark early access predictions with visual indicator.
- FR-062: System shall send early access email to premium subscribers.

_Non-Functional:_

- NFR-030: Early access timing shall be accurate within 5 minutes.

**Dependencies:**

- D032: F015 - Stripe Integration - Assumption: Premium status determines early access.
- D033: F011 - Email Newsletter - Assumption: Newsletter infrastructure supports timed sending.

**Risks:**

- None

**Success Criteria:**

- SC-047: Early Access Timing Accurate - Premium users see predictions 2 hours before free users.
- SC-048: Early Email Sent - Premium subscribers receive early access email.


## Version: v1.0.0

- **Release Date:** 2025-09-01
- **Status:** not_started

### Feature: F019 - Desktop Prediction Bot Application

**Description:** Downloadable desktop application that provides automated prediction access similar to sneaker bots.

**User Stories:**

- **US-045: Download Prediction Bot**

  - Story: As a premium user, I want to download the prediction bot, so that I can run it locally.
  - Acceptance Criteria:
    - AC-086: Given I am premium, when I visit downloads page, then I can download the bot for my OS.
    - AC-087: Given I download the bot, when I run it, then it prompts for API key authentication.

- **US-046: Receive Desktop Notifications**

  - Story: As a bot user, I want desktop notifications when predictions are ready, so that I'm alerted immediately.
  - Acceptance Criteria:
    - AC-088: Given the bot is running, when new predictions are available, then a desktop notification appears.
    - AC-089: Given I click the notification, when the app opens, then today's predictions are displayed.

- **US-047: View Predictions in Bot**

  - Story: As a bot user, I want to view predictions in the desktop app, so that I don't need to visit the website.
  - Acceptance Criteria:
    - AC-090: Given the bot is authenticated, when I open it, then today's predictions are displayed.
    - AC-091: Given predictions are shown, when I view details, then all prediction types are visible.


**Requirements:**

_Functional:_

- FR-063: System shall provide downloadable desktop application for Windows and macOS.
- FR-064: Bot shall authenticate using API key.
- FR-065: Bot shall display desktop notifications for new predictions.
- FR-066: Bot shall display all prediction types with probabilities.
- FR-067: Bot shall auto-update when new versions are available.

_Non-Functional:_

- NFR-031: Bot shall use minimal system resources (under 100MB RAM).
- NFR-032: Bot shall start up in under 5 seconds.

**Dependencies:**

- D034: Electron or Tauri - Assumption: Desktop framework is selected and configured.
- D035: F017 - Prediction API - Assumption: API is available for bot to fetch predictions.

**Risks:**

- **R020: Cross-Platform Compatibility**

  - Overview: Desktop app may have issues on different OS versions.
  - Impact: Support burden increases.
  - Probability: Medium
  - Mitigation: Thorough testing on target platforms; provide clear system requirements.

- **R021: Distribution and Updates**

  - Overview: Managing desktop app distribution and updates is complex.
  - Impact: Users may run outdated versions.
  - Probability: Medium
  - Mitigation: Implement auto-update mechanism; notify users of available updates.


**Success Criteria:**

- SC-049: Bot Downloadable - Premium users can download bot for Windows and macOS.
- SC-050: Authentication Works - Bot authenticates using API key successfully.
- SC-051: Notifications Functional - Desktop notifications appear when predictions are ready.
- SC-052: Predictions Display - All prediction types are viewable in the bot.

### Feature: F020 - V1.0 Stable Release

**Description:** Official stable release with full feature set including ad-supported free tier and premium subscription with bot.

**User Stories:**

- **US-048: Access Complete Platform**

  - Story: As a user, I want access to the complete prediction platform, so that I have all features available.
  - Acceptance Criteria:
    - AC-092: Given v1.0 is released, when I visit the site, then all documented features are available.
    - AC-093: Given I am a free user, when I use the site, then moneyline predictions and performance dashboard are accessible.
    - AC-094: Given I am premium, when I use the platform, then all features including bot are accessible.

- **US-049: Reliable Performance**

  - Story: As a user, I want reliable service performance, so that I can depend on daily predictions.
  - Acceptance Criteria:
    - AC-095: Given the platform is live, when I access it, then uptime exceeds 99.5%.
    - AC-096: Given predictions are published, when I view them, then accuracy continues to exceed 55% threshold.


**Requirements:**

_Functional:_

- FR-068: All features from v0.1.0 through v0.10.0 shall be complete and tested.
- FR-069: Documentation shall be complete for all features.
- FR-070: Free and premium tiers shall have clear feature differentiation.

_Non-Functional:_

- NFR-033: Platform shall achieve 99.5% uptime.
- NFR-034: Prediction accuracy shall maintain 55%+ win rate.
- NFR-035: Platform shall support 10,000+ monthly active users.

**Dependencies:**

- D036: All v0.x Features - Assumption: All features from previous versions are complete.

**Risks:**

- **R022: Market Competition**

  - Overview: Competitors may launch similar transparent prediction services.
  - Impact: Market differentiation reduced.
  - Probability: Medium
  - Mitigation: Build brand and community; continue innovation on features.


**Success Criteria:**

- SC-053: All Features Complete - All planned features are implemented and tested.
- SC-054: Performance Targets Met - Model maintains 55%+ win rate; uptime exceeds 99.5%.
- SC-055: Revenue Generation - Platform generates $1k+ MRR from ads and subscriptions.
- SC-056: User Growth - Platform achieves 5k+ monthly visitors.


