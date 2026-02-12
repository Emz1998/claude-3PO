---
version: v0.1.0
---

# Technical Specifications - Avaris NBA Prediction Platform

## 1. Overview

**Name:** Avaris - NBA Betting Analytics Platform
**Product Description:** A transparent, data-driven NBA game prediction service using XGBoost machine learning to deliver daily picks with verifiable track records. Starting as an ad-supported blog and evolving into a premium subscription platform.

**Core Technology Stack**

- Next.js 15 (React 19)
- TypeScript (strict mode)
- Tailwind CSS v4
- MDX for content
- Supabase (Auth + PostgreSQL)
- Stripe (Payments)
- Python 3.11+ (ML Pipeline)
- XGBoost (Prediction Model)
- Pandas (Data Processing)
- nba_api (Data Source)
- Parquet (Data Storage)

**Dependencies:**

- NBA Stats API (stats.nba.com) - primary data source
- Python nba_api library - API wrapper
- GitHub Actions - CI/CD and scheduled jobs
- Vercel - frontend hosting

**Deployment:**

- Frontend: Vercel (auto-deploy from main branch)
- ML Pipeline: GitHub Actions (scheduled cron jobs)
- Database: Supabase PostgreSQL
- Model Artifacts: Local storage / S3 (future)

**Project Structure:**

```
├── src/
│   ├── app/
│   │   ├── (public)/
│   │   │   ├── page.tsx                 # Homepage with today's picks
│   │   │   ├── predictions/[date]/[matchup]/
│   │   │   └── dashboard/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── signup/
│   │   └── api/
│   │       ├── predictions/
│   │       └── webhooks/
│   ├── components/
│   ├── lib/
│   └── content/
│       └── predictions/                  # Auto-generated MDX
├── ml/
│   ├── data/
│   │   ├── raw/                         # Parquet files
│   │   └── processed/
│   ├── models/
│   ├── pipeline/
│   │   ├── fetch_data.py
│   │   ├── train_model.py
│   │   └── generate_predictions.py
│   └── notebooks/
└── .github/
    └── workflows/
        ├── daily_pipeline.yml
        └── deploy.yml
```

## 2. Architecture Design

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Services                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ NBA Stats API│  │   Supabase   │  │       Stripe         │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Services                            │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │   ML Pipeline    │    │         Next.js API Routes       │  │
│  │  (Python/GH     │────▶│  - /api/predictions              │  │
│  │   Actions)       │    │  - /api/webhooks/stripe          │  │
│  └──────────────────┘    └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                          │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │  Homepage  │  │  Prediction  │  │    Performance       │    │
│  │  (Picks)   │  │   Articles   │  │     Dashboard        │    │
│  └────────────┘  └──────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Core Component Architecture

**ML Pipeline (Python)**

- Scheduled via GitHub Actions (runs nightly at 6 AM EST)
- Fetches team/player stats from NBA Stats API with rate limiting
- Trains XGBoost model on rolling window of current season data
- Generates daily predictions with probabilities
- Outputs predictions as JSON for frontend consumption

**Next.js Frontend**

- Server-side rendered for SEO optimization
- MDX-based blog for prediction articles
- React components for interactive dashboard
- Supabase client for auth and data queries

**Data Layer**

- Parquet files for historical training data (efficient columnar storage)
- Supabase PostgreSQL for predictions, users, and subscriptions
- Local cache for API responses to minimize rate limit impact

### Key Design Decisions

**Local-First ML Training**

- Train models locally/in CI rather than serverless
- Avoids cold start issues and long-running function timeouts
- Model artifacts stored as files, loaded for inference

**MDX for Content**

- Prediction articles auto-generated as MDX files
- Version controlled in git for transparency
- Static generation for optimal SEO

**Parquet over Database for Training Data**

- Efficient storage for time-series ML data
- Easy to partition by season
- No database costs during development

## 3. Data Models

### Schema

**Prediction** (`predictions`)

```typescript
{
  id: string; // UUID
  game_id: string; // NBA game identifier
  game_date: string; // ISO date (YYYY-MM-DD)
  home_team: string; // Team abbreviation (LAL, BOS)
  away_team: string; // Team abbreviation

  // Moneyline prediction (v0.1.0)
  predicted_winner: string; // Team abbreviation
  home_win_probability: number; // 0.0 to 1.0
  confidence: string; // 'low' | 'medium' | 'high'

  // Future-proofing for v1.0.0 (F009: Premium Predictions)
  prediction_type: string; // 'moneyline' (default) | 'spread' | 'total'
  spread_value: number | null; // e.g., -5.5 (populated in v1.0.0)
  spread_pick: string | null; // 'home' | 'away' (populated in v1.0.0)
  total_value: number | null; // e.g., 215.5 (populated in v1.0.0)
  total_pick: string | null; // 'over' | 'under' (populated in v1.0.0)

  // Outcome tracking
  actual_winner: string | null; // Filled after game completes
  is_correct: boolean | null; // Calculated after game
  created_at: string; // ISO timestamp
  updated_at: string; // ISO timestamp
}
```

**Future Considerations:** The `prediction_type`, `spread_*`, and `total_*` fields are nullable and unused in v0.1.0. They enable v1.0.0's premium predictions (F009) without schema migration.

**User** (`users`)

```typescript
{
  id: string; // Supabase auth UID
  email: string; // User email
  subscription_tier: string; // 'free' | 'premium'
  stripe_customer_id: string | null;
  created_at: string;
  updated_at: string;
}
```

**Subscription** (`subscriptions`)

```typescript
{
  id: string; // UUID
  user_id: string; // FK to users
  stripe_subscription_id: string;
  status: string; // 'active' | 'canceled' | 'past_due'
  current_period_end: string; // ISO timestamp
  created_at: string;
}
```

**NewsletterSubscriber** (`newsletter_subscribers`)

```typescript
{
  id: string; // UUID
  email: string; // Subscriber email
  is_verified: boolean; // Email confirmed
  subscribed_at: string;
  unsubscribed_at: string | null;
}
```

### Relationships

```
User (1) ──< (many) Subscription
Prediction (standalone) - no user relationship for public predictions
```

### Indexes

- `predictions(game_date DESC)` - fetch recent predictions
- `predictions(game_date, is_correct)` - performance calculations
- `predictions(game_date, prediction_type)` - filter by prediction type (v1.0.0)
- `users(email)` - login lookup
- `newsletter_subscribers(email)` - deduplication

### Validation

**Prediction:**

- `home_team`, `away_team`: valid NBA team abbreviations (30 teams)
- `home_win_probability`: between 0.0 and 1.0
- `confidence`: enum ('low', 'medium', 'high')
- `game_date`: valid date format, not in future beyond 7 days
- `prediction_type`: enum ('moneyline', 'spread', 'total'), default 'moneyline'
- `spread_pick`: enum ('home', 'away') or null
- `total_pick`: enum ('over', 'under') or null

**User:**

- `email`: valid email format, max 255 chars
- `subscription_tier`: enum ('free', 'premium')

## 4. API/Interface Specifications

### Endpoints

**Get Today's Predictions**

```
GET /api/predictions?date={YYYY-MM-DD}
```

**Request:** Query param `date` (optional, defaults to today)

**Response:**

```typescript
{
  predictions: Array<{
    game_id: string;
    game_date: string;
    home_team: string;
    away_team: string;
    predicted_winner: string;
    home_win_probability: number;
    confidence: string;
    game_time: string; // Local time
  }>;
  meta: {
    total_games: number;
    date: string;
  }
}
```

**Errors:**

- `400` - Invalid date format
- `404` - No predictions for date

**Get Performance Stats**

```
GET /api/performance?period={7d|30d|season}
```

**Response:**

```typescript
{
  total_picks: number;
  wins: number;
  losses: number;
  pending: number;
  win_rate: number; // Percentage
  roi: number; // Assuming flat betting
  streak: {
    type: "win" | "loss";
    count: number;
  }
  last_updated: string;
}
```

**Stripe Webhook**

```
POST /api/webhooks/stripe
```

- Handles `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
- Verifies Stripe signature
- Updates user subscription status

### Internal APIs

**ML Pipeline Interfaces**

`fetch_team_stats(season: str) -> DataFrame`

- **Purpose:** Fetch team performance metrics for a season
- **Example:** `fetch_team_stats("2024-25")` returns DataFrame with all teams

`train_model(data: DataFrame) -> XGBClassifier`

- **Purpose:** Train XGBoost classifier on historical game data
- **Example:** Returns trained model ready for inference

`generate_predictions(model: XGBClassifier, games: List[Game]) -> List[Prediction]`

- **Purpose:** Generate predictions for upcoming games
- **Example:** Returns list of prediction objects with probabilities

## 5. Authentication & Security

### Authentication & Authorization

**Authentication:**

- Method: Supabase Auth (email/password + Google OAuth)
- Session duration: 7 days with refresh tokens
- Email verification required for account activation

**Authorization:**

- Anonymous users: access free predictions and dashboard
- Authenticated users: newsletter preferences, saved picks
- Premium users: access spread/totals predictions (v1.0.0)

### Data Protection

**At Rest:**

- API keys: stored in environment variables (Vercel)
- User data: encrypted by Supabase (AES-256)
- Parquet files: not encrypted (non-sensitive training data)

**In Transit:**

- All API calls: HTTPS/TLS 1.3
- Supabase connections: SSL required

### API Security

**Rate Limiting:**

- NBA Stats API calls: max 10 requests per minute
- Public API endpoints: 100 requests per minute per IP
- Prediction generation: once per day (scheduled job)

**Input Validation:**

- Date parameters: validated against ISO format
- Team abbreviations: validated against enum
- User input: sanitized for XSS

**API Keys:**

- Stored in: Vercel environment variables
- Never exposed in: client-side code, git repository
- Keys used: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

### Privacy & Compliance

**Data Collection:**

- We collect: email, prediction viewing history, subscription status
- We don't collect: betting behavior, financial data, location

**User Rights:**

- Data export: account settings page exports all user data as JSON
- Data deletion: "Delete Account" removes all user data within 30 days

**Compliance:**

- NOT subject to HIPAA/FERPA (per constitution)
- GDPR considerations for EU users (right to erasure)
- CAN-SPAM compliance for newsletter

### Threat Mitigation

**API Abuse:**

- Risk: Bots scraping predictions for resale
- Mitigation: Rate limiting, CAPTCHA on high-volume endpoints

**Data Integrity:**

- Risk: Manipulation of historical prediction records
- Mitigation: Immutable prediction logs, Supabase RLS policies

**Credential Theft:**

- Risk: API keys exposed in logs or client code
- Mitigation: Server-side only key usage, no client-side Stripe secret

## 6. Testing Strategy

### Test Types

**Unit Tests**

- **What:** ML feature engineering, prediction logic, data transformers
- **Tool:** pytest (Python), Vitest (TypeScript)
- **Coverage goal:** 80% of business logic

**Integration Tests**

- **What:** API endpoints, Supabase queries, Stripe webhooks
- **Tool:** pytest with mocks, Next.js testing utilities
- **Focus:** Prediction CRUD, authentication flows

**End-to-End Tests**

- **What:** User flows from homepage to prediction articles
- **Tool:** Playwright
- **Scenarios:** View today's picks, navigate to article, check dashboard

### Critical Test Cases

**Prediction Pipeline:**

- Test: Daily pipeline fetches data and generates predictions
- Expected: All scheduled games have predictions with valid probabilities
- Edge case: No games scheduled (off-season, All-Star break)

**Performance Dashboard:**

- Test: Win rate calculation from historical data
- Expected: Accurate percentage based on verified outcomes
- Edge case: Games still pending (in progress or not played)

**Stripe Subscription:**

- Test: Webhook updates user tier on successful payment
- Expected: User upgraded to premium within 1 minute
- Edge case: Duplicate webhook events (idempotency)

### Test Execution

**When tests run:**

- Unit tests: on every commit (GitHub Actions)
- Integration tests: on PR creation
- E2E tests: before production deployment

**CI/CD integration:**

- GitHub Actions runs tests on PR
- Deployment blocked if tests fail
- Coverage report uploaded as artifact

### Coverage Goals

- Minimum coverage: 70% overall
- Must cover: Prediction logic (90%), API endpoints (80%)
- Can skip: Generated MDX content, third-party library wrappers

### Mocking

**External services mocked:**

- NBA Stats API: Recorded responses for consistent testing
- Supabase: Local PostgreSQL or mock client
- Stripe: Test mode with mock webhooks

### Performance & Optimization

**Performance Targets:**

- Page load time: <2s on 3G
- API response time: <500ms
- Lighthouse SEO score: 90+

**Optimization Strategies:**

- Static generation for prediction articles (ISR with 1-hour revalidation)
- Image optimization with Next.js Image component
- Code splitting for dashboard components

**Bottleneck Monitoring:**

- Tool: Vercel Analytics
- Metrics: Core Web Vitals (LCP, FID, CLS)

## 7. Deployment & Operations

### Build Process

**Development:**

```bash
npm run dev              # Start Next.js dev server
cd ml && python -m pytest tests/  # Run ML tests
```

**Production:**

```bash
npm run build            # Build Next.js for production
cd ml && python pipeline/train_model.py  # Train model
```

**Environment variables:**

- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Public anon key
- `SUPABASE_SERVICE_ROLE_KEY`: Server-side operations
- `STRIPE_SECRET_KEY`: Stripe API key
- `STRIPE_WEBHOOK_SECRET`: Webhook signature verification

### Deployment

**Platform:** Vercel (frontend), GitHub Actions (ML pipeline)

**Steps:**

1. Push to main branch triggers Vercel deployment
2. Vercel builds and deploys Next.js app
3. GitHub Actions runs daily pipeline at 6 AM EST
4. Pipeline pushes predictions to Supabase

**Frequency:**

- Frontend: on every merge to main (automated)
- ML pipeline: daily at 6 AM EST (cron)
- Model retraining: nightly with previous day's results

### Monitoring

**Metrics tracked:**

- Prediction accuracy: calculated daily, stored in Supabase
- API response times: Vercel Analytics
- Pipeline success rate: GitHub Actions logs

**Error tracking:** Vercel logs (basic), Sentry (future)

**Alerts:**

- GitHub Actions failure: email notification
- Stripe webhook failure: logged to Supabase

### Observability & Telemetry

**Logging:**

- Structured logging format: JSON
- Log levels: INFO for requests, ERROR for failures
- Log aggregation: Vercel logs
- Retention: 7 days (Vercel free tier)

**Metrics:**

- Business metrics: total predictions, win rate, subscriber count
- Technical metrics: API latency, error rate

### Rollback

**If deployment fails:**

1. Revert commit in git
2. Vercel auto-deploys previous version
3. Verify with health check endpoint

**Database migrations:**

- Use Supabase migrations with up/down scripts
- Test on staging project first

### Maintenance

**Updates:** Weekly dependency updates, monthly major upgrades
**Backups:** Supabase automatic daily backups (7-day retention)
**Dependencies:** nba_api monitored for breaking changes (historically unstable)

### Disaster Recovery

**Backup Strategy:**

- RTO: 4 hours (restore from backup)
- RPO: 24 hours (daily backups)
- Backup testing: monthly restore verification

**Failure Scenarios:**

- NBA API down: use cached data, skip daily update
- Supabase outage: static site continues serving, writes fail
- Model corruption: restore from git-versioned artifact

## 8. Implementation Details

### Core Features

**NBA Data Pipeline (F001)**

**How it works:**

1. GitHub Actions cron triggers at 6 AM EST
2. Python script fetches team stats from NBA Stats API with rate limiting
3. Data transformed and appended to Parquet files
4. Feature engineering creates model-ready dataset

**Key logic:**

- Exponential backoff for API rate limits (2s, 4s, 8s delays)
- Rolling 10-game window for "recent form" features
- Back-to-back detection based on game schedule

**Code snippet:**

```python
def fetch_with_retry(endpoint: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            response = endpoint.get_data_frames()[0]
            return response
        except Exception as e:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    raise Exception(f"Failed after {max_retries} retries")
```

**XGBoost Prediction Model (F002)**

**How it works:**

1. Load historical data from Parquet files
2. Engineer features: team stats, player availability, situational factors
3. Train XGBoost classifier with time-series cross-validation
4. Generate predictions for today's games with probability output

**Key logic:**

- Features: win rate, point differential, home/away splits, rest days
- Target: binary classification (home team wins = 1)
- Confidence: probability thresholds (>65% = high, >55% = medium)

**Code snippet:**

```python
model = XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    objective='binary:logistic'
)
model.fit(X_train, y_train)
probabilities = model.predict_proba(X_test)[:, 1]
```

### Technical Decisions

**Moneyline First, Spreads Later**

- **Choice:** Start with moneyline predictions only
- **Why:** Simpler model, clearer success metric (win/loss)
- **Alternative considered:** All bet types at once - rejected for MVP scope

**Daily Retraining**

- **Choice:** Retrain model nightly with latest results
- **Why:** Capture current season dynamics and team form
- **Alternative considered:** Weekly retraining - rejected for freshness

### Algorithms

**Win Probability Calibration**

- **Purpose:** Ensure predicted probabilities match actual outcomes
- **Approach:** Platt scaling on holdout validation set
- **Validation:** Calibration curve should follow diagonal

**Feature Importance Analysis**

- **Purpose:** Understand which factors drive predictions
- **Approach:** XGBoost built-in feature importance (gain method)
- **Usage:** Display in article content for transparency

### Edge Cases

**No games scheduled:** Pipeline succeeds but generates empty predictions list
**Game postponed:** Mark prediction as "void", exclude from accuracy stats
**Tie game:** N/A for NBA (overtime until winner)
**API rate limit exceeded:** Retry with exponential backoff, fail gracefully after 3 attempts

## 9. Future Work

### Future Features (Post-MVP)

**Spread & Totals Predictions (v1.0.0):**

- **Description:** Extend model to predict point spreads and over/under totals
- **Why later:** Harder to model than moneyline, needs proven accuracy first
- **Priority:** High (premium feature)

**Prediction Bot Desktop App:**

- **Description:** Downloadable CLI/app for programmatic pick access
- **Why later:** Requires proven performance and subscriber base
- **Priority:** Medium (unique differentiator)

**API Access for Premium:**

- **Description:** REST API for power users to integrate picks
- **Why later:** Need subscription infrastructure first
- **Priority:** Medium

### Known Technical Debt

| ID     | Component  | Issue                        | Impact                   | Effort | Priority |
| ------ | ---------- | ---------------------------- | ------------------------ | ------ | -------- |
| TD-001 | Pipeline   | No retry for Supabase writes | Data loss on DB errors   | 1 day  | High     |
| TD-002 | Model      | No model versioning          | Can't rollback bad model | 2 days | Medium   |
| TD-003 | Testing    | No E2E tests for pipeline    | Missed failures          | 3 days | Medium   |
| TD-004 | Monitoring | Basic logging only           | Hard to debug issues     | 2 days | Low      |

### Out of Scope

- Real-time live game predictions (in-play betting)
- Player prop predictions (points, rebounds, assists)
- Multi-sport expansion (NFL, MLB, NHL)
- Mobile native apps (iOS, Android)
- Social features and leaderboards

### Research Needed

**Alternative Data Sources:**

- **What:** Evaluate paid data providers vs free NBA API
- **Why:** Free API may become unreliable; paid sources offer more features
- **Estimated effort:** 1 week

**Ensemble Methods:**

- **What:** Test Random Forest, Neural Network alongside XGBoost
- **Why:** May improve accuracy through model stacking
- **Estimated effort:** 2 weeks
