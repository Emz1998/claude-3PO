# Avaris - Product Requirements Document

## Metadata

- **Current Version:** v0.1.0
- **Stable Version:** v1.0.0
- **Last Updated:** 2025-12-25
- **Updated By:** Claude Code

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
- **Elevator Pitch:** A transparent, data-driven NBA game prediction service using XGBoost machine learning to deliver daily picks with verifiable track records, starting as an ad-supported blog and evolving into a premium subscription platform.
- **Industry Problem:** Sports betting markets are saturated with tout services making questionable claims without transparent track records. Casual and serious bettors lack access to reliable, data-driven predictions with accountability. Existing prediction services either hide their historical performance or cherry-pick winning streaks.
- **Solutions:**
  - Build XGBoost ML model trained on NBA Stats API data for game outcome predictions
  - Launch ad-supported blog with daily predictions in SEO-optimized article format
  - Display transparent performance dashboard showing win rate, ROI, and historical results
  - Automate daily prediction pipeline using scheduled jobs for fresh picks each morning
  - Transition to subscription model once 55%+ win rate threshold is achieved
  - Develop desktop prediction bot application for premium programmatic access
  - Provide tiered service for casual bettors (free moneyline) and serious bettors (premium spreads/totals)
- **Goals:**
  - Achieve 55%+ win rate over 100+ predictions to beat break-even threshold
  - Build transparent track record through publicly displayed historical performance
  - Launch MVP ad-supported blog with daily picks and performance dashboard
  - Generate 5k+ monthly visitors through SEO and content marketing
  - Reach $1k-5k MRR from ads and early subscribers within 12 months
  - Develop subscription tiers with premium features (spreads, totals, API access)

## Tech Stack

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS v4
- MDX
- Supabase (Auth + PostgreSQL)
- Stripe
- Python 3.11+
- XGBoost
- Pandas
- nba_api
- Parquet
- GitHub Actions (CI/CD)
- Vercel (Hosting)

## Version: v0.1.0 (**MVP**)

- **Release Date:** 2025-01-15
- **Status:** not_started

### Feature: F001 - NBA Data Pipeline

**Description:** Automated data ingestion system that fetches team stats, player stats, game schedules, and historical data from the NBA Stats API. Stores data in Parquet files for efficient ML training and inference.

**User Stories:**

- **US-001: Fetch Team Performance Data**

  - Story: As a data engineer, I want to automatically fetch current team statistics from NBA API, so that the model has up-to-date team performance metrics for predictions.
  - Acceptance Criteria:
    - AC-001: Given the pipeline runs daily, when it fetches team stats, then all 30 NBA teams have updated win rates, point differentials, and offensive/defensive ratings.
    - AC-002: Given API rate limits exist, when fetching data, then the pipeline respects rate limits and implements exponential backoff.

- **US-002: Fetch Player Statistics**

  - Story: As a data engineer, I want to collect key player statistics and injury reports, so that the model can factor in player availability and performance.
  - Acceptance Criteria:
    - AC-003: Given a game is scheduled, when the pipeline runs, then it retrieves stats for all rostered players on both teams.
    - AC-004: Given injury data is available, when processing player data, then injury status is captured and stored.

- **US-003: Store Historical Data**

  - Story: As a data engineer, I want to store historical game results and statistics in Parquet format, so that the model can be trained on past seasons.
  - Acceptance Criteria:
    - AC-005: Given historical data is fetched, when stored, then data is partitioned by season in Parquet format.
    - AC-006: Given 2022-23 and 2023-24 seasons, when backfilling data, then all regular season games are captured with complete statistics.

**Requirements:**

_Functional:_

- FR-001: Pipeline fetches team standings, records, and conference rankings daily.
- FR-002: Pipeline fetches player per-game stats, usage rates, and plus/minus metrics.
- FR-003: Pipeline fetches upcoming game schedules with home/away designations.
- FR-004: Pipeline stores all data in Parquet files with date-based partitioning.
- FR-005: Pipeline logs all fetch operations and errors for debugging.

_Non-Functional:_

- NFR-001: Pipeline completes daily data refresh within 30 minutes.
- NFR-002: Pipeline handles API failures gracefully with retry logic.
- NFR-003: Data storage uses less than 1GB for current season data.

**Dependencies:**

- D001: NBA Stats API (stats.nba.com) - Assumption: API remains publicly accessible with rate limiting.
- D002: Python nba_api library - Assumption: Library is maintained and compatible with current API endpoints.

**Risks:**

- **R001: NBA API Rate Limiting**

  - Overview: The NBA Stats API may impose strict rate limits or block requests.
  - Impact: Data pipeline cannot fetch required statistics, blocking model training.
  - Probability: High
  - Mitigation: Implement caching, respect rate limits, use exponential backoff, and store data locally to minimize API calls.

- **R002: API Structure Changes**

  - Overview: NBA may change API endpoints or response formats without notice.
  - Impact: Pipeline breaks and requires code updates to adapt.
  - Probability: Medium
  - Mitigation: Abstract API calls behind interfaces, implement schema validation, monitor for breaking changes.

**Success Criteria:**

- SC-001: Complete Data Coverage - Pipeline successfully fetches and stores data for all 30 NBA teams and their players.
- SC-002: Historical Backfill Complete - 2022-23 and 2023-24 season data is fully backfilled for model training.
- SC-003: Reliable Daily Updates - Pipeline runs successfully for 7 consecutive days without manual intervention.

### Feature: F002 - XGBoost Prediction Model

**Description:** Machine learning model using XGBoost to predict NBA game outcomes (moneyline). Trained on historical data with features including team performance, player stats, and situational factors.

**User Stories:**

- **US-004: Train Prediction Model**

  - Story: As a data scientist, I want to train an XGBoost model on historical NBA data, so that it can predict game winners with measurable accuracy.
  - Acceptance Criteria:
    - AC-007: Given historical data from 2022-24 seasons, when training the model, then cross-validation accuracy exceeds 52% (break-even threshold).
    - AC-008: Given model is trained, when evaluated on holdout set, then log loss and calibration metrics are within acceptable ranges.

- **US-005: Generate Daily Predictions**

  - Story: As a system, I want to generate predictions for today's games each morning, so that picks are available before game time.
  - Acceptance Criteria:
    - AC-009: Given games are scheduled today, when inference runs, then each game has a predicted winner with probability percentage.
    - AC-010: Given predictions are generated, when stored, then they include game ID, teams, predicted winner, and confidence score.

- **US-006: Retrain Model Nightly**

  - Story: As a data scientist, I want the model to retrain nightly with latest results, so that it captures current season dynamics.
  - Acceptance Criteria:
    - AC-011: Given yesterday's games completed, when nightly retraining runs, then new results are incorporated into training data.
    - AC-012: Given retraining completes, when new model is deployed, then it replaces the previous model for inference.

**Requirements:**

_Functional:_

- FR-006: Model uses team performance features: win rates, point differentials, offensive/defensive ratings, recent form (L5, L10).
- FR-007: Model uses player features: key player stats, injury status, rest days, usage rates.
- FR-008: Model uses situational features: home/away, back-to-backs, travel distance, division matchups.
- FR-009: Model outputs predicted winner and win probability for each game.
- FR-010: Model retrains nightly with rolling window of current season data.

_Non-Functional:_

- NFR-004: Model inference completes within 5 seconds for all daily games.
- NFR-005: Nightly retraining completes within 15 minutes.
- NFR-006: Model achieves 55%+ win rate target over 50+ predictions before public launch.

**Dependencies:**

- D003: F001 - NBA Data Pipeline - Assumption: Data pipeline provides clean, structured data for model training.
- D004: XGBoost Python library - Assumption: Library is stable and well-documented for classification tasks.

**Risks:**

- **R003: Model Underperformance**

  - Overview: XGBoost model may not achieve 55%+ win rate target.
  - Impact: Cannot launch public service without proven performance threshold.
  - Probability: Medium
  - Mitigation: Iterate on feature engineering, hyperparameter tuning, and ensemble methods. Paper trade extensively before launch.

- **R004: Overfitting to Historical Data**

  - Overview: Model may overfit to past seasons and fail on current games.
  - Impact: High backtesting accuracy but poor live performance.
  - Probability: Medium
  - Mitigation: Use time-series cross-validation, rolling window training, and holdout validation on recent games.

**Success Criteria:**

- SC-004: Backtesting Performance - Model achieves 55%+ accuracy on 2023-24 season holdout data.
- SC-005: Paper Trading Validation - Model achieves 55%+ win rate over 50+ live predictions in paper trading mode.
- SC-006: Automated Pipeline - Nightly retraining and daily inference run automatically without intervention.

## Version: v0.2.0

- **Release Date:** 2025-02-15
- **Status:** not_started

### Feature: F003 - Daily Picks Blog

**Description:** Next.js blog with auto-generated daily picks articles in SEO-optimized format. Each game gets a dedicated page with prediction, analysis, and historical context.

**User Stories:**

- **US-007: View Today's Picks**

  - Story: As a visitor, I want to see today's NBA game predictions on the homepage, so that I can quickly access current picks.
  - Acceptance Criteria:
    - AC-013: Given I visit the homepage, when today has scheduled games, then I see a list of all picks with predicted winners and confidence percentages.
    - AC-014: Given picks are displayed, when viewing each pick, then I see team names, game time, and predicted winner highlighted.

- **US-008: Read Game Prediction Article**

  - Story: As a visitor, I want to read detailed prediction articles for each game, so that I understand the reasoning behind picks.
  - Acceptance Criteria:
    - AC-015: Given I click on a game prediction, when the article loads, then I see matchup analysis, key stats, and prediction rationale.
    - AC-016: Given the article is indexed, when searching for '[Team A] vs [Team B] prediction', then the page appears in search results.

- **US-009: Auto-Generate Daily Articles**

  - Story: As a content system, I want to automatically generate MDX articles each morning, so that fresh content is ready without manual work.
  - Acceptance Criteria:
    - AC-017: Given predictions are generated, when article generation runs, then each game has an MDX file created with proper frontmatter.
    - AC-018: Given articles are generated, when the site builds, then all new articles are accessible at their SEO-friendly URLs.

**Requirements:**

_Functional:_

- FR-011: Homepage displays today's picks with game times, teams, and predictions.
- FR-012: Individual game pages follow format: '/predictions/[date]/[team-a]-vs-[team-b]'.
- FR-013: Articles include SEO meta tags, structured data, and social sharing cards.
- FR-014: Content generation pipeline creates MDX files from prediction data.

_Non-Functional:_

- NFR-007: Pages load within 2 seconds on 3G connection.
- NFR-008: Site achieves 90+ Lighthouse SEO score.
- NFR-009: Articles are generated and published by 8 AM ET daily.

**Dependencies:**

- D005: F002 - XGBoost Prediction Model - Assumption: Daily predictions are available for article generation.
- D006: Next.js with MDX support - Assumption: Next.js MDX integration works for dynamic content generation.

**Risks:**

- **R005: SEO Competition**

  - Overview: Established sports sites may dominate search rankings for game prediction keywords.
  - Impact: Organic traffic growth slower than projected.
  - Probability: High
  - Mitigation: Focus on long-tail keywords, build quality backlinks, emphasize unique transparency angle.

**Success Criteria:**

- SC-007: Content Pipeline Active - Daily articles are auto-generated and published for 14 consecutive days.
- SC-008: SEO Indexing - Google indexes prediction articles within 48 hours of publication.

## Version: v0.3.0

- **Release Date:** 2025-03-15
- **Status:** not_started

### Feature: F004 - Performance Dashboard

**Description:** Public dashboard displaying historical prediction performance including win rate, ROI, streak data, and complete pick history. Transparency as competitive advantage.

**User Stories:**

- **US-010: View Overall Performance**

  - Story: As a visitor, I want to see the overall prediction track record, so that I can evaluate the service's credibility.
  - Acceptance Criteria:
    - AC-019: Given I visit the dashboard, when viewing stats, then I see total picks, wins, losses, win rate percentage, and ROI.
    - AC-020: Given historical data exists, when displayed, then all metrics are calculated from verifiable pick history.

- **US-011: View Recent Results**

  - Story: As a visitor, I want to see recent prediction results, so that I can assess current model performance.
  - Acceptance Criteria:
    - AC-021: Given recent games completed, when viewing results, then I see last 10 predictions with outcomes marked.
    - AC-022: Given a prediction was made, when the game completes, then the result is automatically updated.

- **US-012: Browse Pick History**

  - Story: As a visitor, I want to browse complete pick history, so that I can verify no cherry-picking occurred.
  - Acceptance Criteria:
    - AC-023: Given I access pick history, when browsing, then every prediction ever made is listed with date, pick, and outcome.
    - AC-024: Given history is public, when filtering by date range, then results show all picks in that period.

**Requirements:**

_Functional:_

- FR-015: Dashboard calculates and displays overall win rate and ROI.
- FR-016: Dashboard shows last N predictions with win/loss indicators.
- FR-017: Dashboard provides filterable, searchable complete pick history.
- FR-018: Results are automatically updated when games complete.

_Non-Functional:_

- NFR-010: Dashboard loads within 3 seconds with full history.
- NFR-011: Historical data is immutable to ensure transparency.

**Dependencies:**

- D007: F002 - XGBoost Prediction Model - Assumption: All predictions are logged with timestamps before games start.
- D008: Supabase PostgreSQL - Assumption: Database stores all picks and game outcomes for querying.

**Risks:**

- **R006: Model Performance Exposure**

  - Overview: Public dashboard exposes poor performance if model underperforms.
  - Impact: Credibility damage if win rate drops below break-even.
  - Probability: Medium
  - Mitigation: Paper trade extensively before public launch; have minimum performance threshold before going live.

**Success Criteria:**

- SC-009: Full Transparency - 100% of predictions are publicly visible with verifiable outcomes.
- SC-010: Automated Updates - Game outcomes update dashboard within 1 hour of game completion.

## Version: v0.4.0

- **Release Date:** 2025-04-15
- **Status:** not_started

### Feature: F005 - Ad Monetization

**Description:** Google AdSense integration for initial monetization. Strategic ad placement that balances revenue with user experience.

**User Stories:**

- **US-013: Display Advertisements**

  - Story: As a site owner, I want to display ads on the site, so that traffic generates revenue.
  - Acceptance Criteria:
    - AC-025: Given AdSense is configured, when pages load, then ads display in designated placements.
    - AC-026: Given ads are displayed, when viewing on mobile, then ads are responsive and non-intrusive.

**Requirements:**

_Functional:_

- FR-019: AdSense ads display on homepage, article pages, and dashboard.
- FR-020: Ad placements follow Google AdSense policies.

_Non-Functional:_

- NFR-012: Ads do not degrade page load time by more than 500ms.
- NFR-013: Ad density complies with Better Ads Standards.

**Dependencies:**

- D009: Google AdSense account approval - Assumption: Site has sufficient content and traffic for AdSense approval.

**Risks:**

- **R007: AdSense Rejection**

  - Overview: Google may reject AdSense application due to content policy concerns with betting content.
  - Impact: Primary monetization strategy blocked.
  - Probability: Medium
  - Mitigation: Position as sports analytics/predictions (not gambling); have backup ad networks identified.

**Success Criteria:**

- SC-011: AdSense Approved - Google AdSense account is approved and ads are serving.
- SC-012: Revenue Generation - Site generates measurable ad revenue within first month of traffic.

### Feature: F006 - Email Newsletter

**Description:** Daily email newsletter with picks digest. Builds owned audience for future subscription conversion.

**User Stories:**

- **US-014: Subscribe to Newsletter**

  - Story: As a visitor, I want to subscribe to daily picks via email, so that I receive predictions in my inbox.
  - Acceptance Criteria:
    - AC-027: Given I enter my email, when I subscribe, then I receive a confirmation email.
    - AC-028: Given I am subscribed, when picks are published daily, then I receive an email with today's predictions.

- **US-015: Manage Subscription**

  - Story: As a subscriber, I want to unsubscribe easily, so that I control my email preferences.
  - Acceptance Criteria:
    - AC-029: Given I receive a newsletter, when I click unsubscribe, then I am removed from the list.

**Requirements:**

_Functional:_

- FR-021: Email capture form on homepage and article pages.
- FR-022: Daily automated email with today's picks sent by 9 AM ET.
- FR-023: Unsubscribe link in every email that works immediately.

_Non-Functional:_

- NFR-014: Email deliverability rate above 95%.
- NFR-015: Comply with CAN-SPAM and GDPR requirements.

**Dependencies:**

- D010: Email service provider (e.g., Resend, SendGrid) - Assumption: Email provider supports transactional and marketing emails.

**Risks:**

- **R008: Spam Filtering**

  - Overview: Emails may be caught by spam filters, reducing deliverability.
  - Impact: Subscribers don't receive picks, reducing engagement.
  - Probability: Medium
  - Mitigation: Use reputable email provider, implement proper SPF/DKIM/DMARC, warm up IP gradually.

**Success Criteria:**

- SC-013: Subscriber Growth - Acquire 500+ email subscribers within 3 months of launch.
- SC-014: Engagement Metrics - Newsletter open rate above 30%, click rate above 5%.

## Version: v1.0.0

- **Release Date:** 2025-06-15
- **Status:** not_started

### Feature: F007 - User Authentication

**Description:** Supabase-based authentication system supporting email/password and social logins. Foundation for premium subscription features.

**User Stories:**

- **US-016: Create Account**

  - Story: As a visitor, I want to create an account, so that I can access premium features when available.
  - Acceptance Criteria:
    - AC-030: Given I provide email and password, when I sign up, then an account is created and I receive verification email.
    - AC-031: Given I have a Google account, when I click sign in with Google, then I am authenticated via OAuth.

- **US-017: Login to Account**

  - Story: As a user, I want to log into my account, so that I can access personalized features.
  - Acceptance Criteria:
    - AC-032: Given I have an account, when I enter correct credentials, then I am logged in and redirected.
    - AC-033: Given I am logged in, when I return to the site, then my session persists for 7 days.

**Requirements:**

_Functional:_

- FR-024: Support email/password authentication with email verification.
- FR-025: Support Google OAuth social login.
- FR-026: Password reset flow via email.
- FR-027: Session management with secure token handling.

_Non-Functional:_

- NFR-016: Authentication flows complete within 3 seconds.
- NFR-017: Follow OWASP authentication security best practices.

**Dependencies:**

- D011: Supabase Auth - Assumption: Supabase provides reliable auth infrastructure.

**Risks:**

- **R009: Security Vulnerabilities**

  - Overview: Authentication system may have security flaws.
  - Impact: User accounts compromised, legal and reputation damage.
  - Probability: Low
  - Mitigation: Use Supabase managed auth, implement security best practices, regular security reviews.

**Success Criteria:**

- SC-015: Auth System Live - Users can create accounts and log in via email or Google.
- SC-016: Security Audit Passed - No critical vulnerabilities in authentication flows.

### Feature: F008 - Subscription Payments

**Description:** Stripe integration for premium subscription management. Monthly recurring billing with free tier for moneyline picks.

**User Stories:**

- **US-018: Subscribe to Premium**

  - Story: As a user, I want to subscribe to a premium plan, so that I can access spreads, totals, and advanced features.
  - Acceptance Criteria:
    - AC-034: Given I am logged in, when I select a premium plan and enter payment, then my subscription is activated.
    - AC-035: Given I am subscribed, when I access premium content, then I can view spreads and totals predictions.

- **US-019: Manage Subscription**

  - Story: As a subscriber, I want to manage my subscription, so that I can upgrade, downgrade, or cancel.
  - Acceptance Criteria:
    - AC-036: Given I have a subscription, when I access billing settings, then I can view and modify my plan.
    - AC-037: Given I cancel, when the billing period ends, then my access reverts to free tier.

**Requirements:**

_Functional:_

- FR-028: Stripe Checkout integration for subscription signup.
- FR-029: Customer portal for subscription management.
- FR-030: Webhook handling for subscription lifecycle events.
- FR-031: Tier-based access control for premium content.

_Non-Functional:_

- NFR-018: Payment processing completes within 5 seconds.
- NFR-019: PCI DSS compliance via Stripe's hosted checkout.

**Dependencies:**

- D012: Stripe - Assumption: Stripe account approved for recurring billing.
- D013: F007 - User Authentication - Assumption: Users must be authenticated to subscribe.

**Risks:**

- **R010: Payment Processing Issues**

  - Overview: Stripe may flag or restrict account for betting-related content.
  - Impact: Cannot process payments, blocking monetization.
  - Probability: Low
  - Mitigation: Position as sports analytics, review Stripe's acceptable use policy, have backup processor identified.

**Success Criteria:**

- SC-017: Payments Processing - Users can successfully subscribe and make payments via Stripe.
- SC-018: MRR Milestone - Achieve $1k MRR within 3 months of subscription launch.

### Feature: F009 - Premium Predictions (Spreads & Totals)

**Description:** Extended prediction coverage for point spreads and over/under totals. Premium-only feature for paying subscribers.

**User Stories:**

- **US-020: View Spread Predictions**

  - Story: As a premium subscriber, I want to see point spread predictions, so that I can make more informed betting decisions.
  - Acceptance Criteria:
    - AC-038: Given I am a premium subscriber, when I view today's picks, then I see spread predictions alongside moneyline.
    - AC-039: Given a spread prediction, when displayed, then it shows predicted spread and confidence level.

- **US-021: View Totals Predictions**

  - Story: As a premium subscriber, I want to see over/under predictions, so that I have complete game analysis.
  - Acceptance Criteria:
    - AC-040: Given I am a premium subscriber, when I view picks, then I see over/under predictions with projected total.

**Requirements:**

_Functional:_

- FR-032: Model generates spread predictions with confidence scores.
- FR-033: Model generates over/under predictions with projected totals.
- FR-034: Premium content gated behind subscription check.

_Non-Functional:_

- NFR-020: Spread and totals predictions achieve 52%+ accuracy (break-even for standard vig).

**Dependencies:**

- D014: F002 - XGBoost Prediction Model - Assumption: Model extended to predict spreads and totals.
- D015: F008 - Subscription Payments - Assumption: Subscription status determines content access.

**Risks:**

- **R011: Spread/Totals Model Underperformance**

  - Overview: Predicting spreads and totals may be harder than moneyline.
  - Impact: Premium feature doesn't deliver value, hurting retention.
  - Probability: Medium
  - Mitigation: Extensive backtesting before launch; clearly communicate that spreads/totals are harder markets.

**Success Criteria:**

- SC-019: Premium Predictions Live - Spread and totals predictions available to premium subscribers.
- SC-020: Premium Performance - Spread predictions achieve 52%+ win rate over first 100 picks.
