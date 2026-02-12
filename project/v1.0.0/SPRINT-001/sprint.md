# Sprint

**Project:** Avaris
**Sprint #:** 1
**Goal:** Establish foundational infrastructure and ML pipeline for NBA prediction model
**Dates:** 2026-02-17 → 2026-03-02
**Capacity:** 80 hours (2 weeks, full-time solo developer)

---

## Story Types

| Prefix | Type            | Format                                               | When to Use                                      |
| ------ | --------------- | ---------------------------------------------------- | ------------------------------------------------ |
| US-NNN | User Story      | As a `[role]`, I want `[what]` so that `[why]`       | User-facing feature or behavior                  |
| TS-NNN | Technical Story | As a `[dev/system]`, I need `[what]` so that `[why]` | Infrastructure, refactors, non-user-facing work  |
| BG-NNN | Bug             | `[What's broken]` — Expected: `[X]`, Actual: `[Y]`   | Defect in existing functionality                 |
| SK-NNN | Spike           | Investigate `[question]` to decide `[decision]`      | Research needed before committing to an approach |

---

## Sprint Overview

> Quick-glance table of everything in this sprint. Update statuses here daily.

| ID     | Type  | Epic   | Title                                                | Points | Status | Depends On     | Blocked By |
| ------ | ----- | ------ | ---------------------------------------------------- | ------ | ------ | -------------- | ---------- |
| SK-001 | Spike | EP-001 | Which NBA stats features yield best XGBoost accuracy | 2      | Todo   | -              |            |
| SK-002 | Spike | EP-001 | Pre-market vs post-line-release prediction timing    | 1      | Todo   | -              |            |
| TS-012 | Tech  | -      | Next.js 15 project setup                             | 3      | Todo   | -              |            |
| TS-013 | Tech  | -      | Firebase Firestore configuration                     | 2      | Todo   | -              |            |
| TS-016 | Tech  | -      | Python ML pipeline project setup                     | 2      | Todo   | -              |            |
| TS-001 | Tech  | EP-001 | NBA Stats API data ingestion                         | 5      | Todo   | TS-016         |            |
| TS-002 | Tech  | EP-001 | XGBoost model training pipeline                      | 8      | Todo   | SK-001, TS-001 |            |

**Total Points:** 23

---

## Sprint Backlog

### Spikes

#### SK-001: Which NBA stats features yield best XGBoost accuracy

> **Investigate:** Which NBA statistics (team stats, player stats, situational factors) yield the best XGBoost prediction accuracy
> **To decide:** The optimal feature set for model v1 to maximize win rate
> **Timebox:** 8 hours

**Depends on:** -
**Status:** Todo
**Points:** M (2)

**Deliverable:**

- [ ] Feature importance analysis documented in decisions.md with top 10 features ranked
- [ ] Recommendation includes feature set with pros/cons and expected accuracy impact
- [ ] Prototype training script tests at least 3 different feature combinations

> Spikes do NOT go through the QA / Code Reviewer pipeline.
> They produce a decision, not shippable code.

---

#### SK-002: Pre-market vs post-line-release prediction timing

> **Investigate:** Should predictions be generated before betting markets open or after sportsbook lines are released
> **To decide:** Pipeline timing and data dependency strategy
> **Timebox:** 4 hours

**Depends on:** -
**Status:** Todo
**Points:** S (1)

**Deliverable:**

- [ ] Decision documented in decisions.md with timing recommendation
- [ ] Trade-off analysis includes data freshness, line availability, and user value
- [ ] Cron schedule recommendation for daily pipeline execution

> Spikes do NOT go through the QA / Code Reviewer pipeline.
> They produce a decision, not shippable code.

---

### Technical Stories

#### TS-012: Next.js 15 project setup

> **As a** developer, **I need** to set up Next.js 15 with TypeScript strict mode, ESLint, and Prettier **so that** the web app has a solid foundation

**Priority:** Must
**Story Points:** 3
**Depends on:** -
**Status:** Todo

**Acceptance Criteria (Story Level):**

- [ ] `npm run dev` starts development server without errors
- [ ] `npm run build` completes successfully with production-ready output
- [ ] TypeScript strict mode compilation passes with zero errors
- [ ] ESLint and Prettier configured and running without warnings
- [ ] Project follows architecture.md folder structure

**Tasks:**

- **T-001:** Initialize Next.js 15 project with App Router and TypeScript
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** -
  - **Acceptance Criteria (Task Level):**
    - [ ] Next.js 15 project scaffolded using `create-next-app`
    - [ ] TypeScript configured with strict mode in tsconfig.json
    - [ ] App Router structure created with basic routes
  - **Files touched:** `package.json`, `tsconfig.json`, `next.config.js`, `src/app/page.tsx`, `src/app/layout.tsx`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Use `npx create-next-app@latest` with TypeScript and App Router. Enable strict mode in tsconfig. Verify no compilation errors.

- **T-002:** Configure ESLint and Prettier with project standards
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** T-001
  - **Acceptance Criteria (Task Level):**
    - [ ] ESLint configured with Next.js and TypeScript rules
    - [ ] Prettier configured with consistent formatting rules
    - [ ] `npm run lint` passes without errors or warnings
  - **Files touched:** `.eslintrc.json`, `.prettierrc`, `package.json`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Follow coding-standards.md for ESLint and Prettier configuration. Set up format-on-save in editor config.

- **T-003:** Create project folder structure per architecture.md
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** T-001
  - **Acceptance Criteria (Task Level):**
    - [ ] All directories from architecture.md created (src/app, src/components, src/lib, public)
    - [ ] Barrel index.ts files added where appropriate
    - [ ] README.md created with setup instructions
  - **Files touched:** `src/app/`, `src/components/`, `src/lib/`, `src/types/`, `public/`, `README.md`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Match exact folder structure from architecture.md Section "Project Structure". Create placeholder index.ts files for clean imports.

---

#### TS-013: Firebase Firestore configuration

> **As a** developer, **I need** to configure Firebase Firestore with collection schemas and security rules **so that** data is structured and secure

**Priority:** Must
**Story Points:** 2
**Depends on:** -
**Status:** Todo

**Acceptance Criteria (Story Level):**

- [ ] Firebase project created and connected to application
- [ ] Firestore collections (predictions, performance, blog_metadata) created with correct schema
- [ ] Security rules enforce read-only access for client, write access for service account
- [ ] Environment variables configured for Firebase credentials

**Tasks:**

- **T-004:** Create Firebase project and configure credentials
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** -
  - **Acceptance Criteria (Task Level):**
    - [ ] Firebase project created in Firebase console
    - [ ] Service account key generated and stored securely
    - [ ] Environment variables added to .env.local and .env.example
  - **Files touched:** `.env.local`, `.env.example`, Firebase console
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Use Firebase free Spark plan. Never commit service account key. Store in GitHub Secrets for CI/CD.

- **T-005:** Initialize Firestore SDK and create collection schemas
  - **Status:** Todo
  - **Complexity:** M
  - **Depends on:** T-004
  - **Acceptance Criteria (Task Level):**
    - [ ] Firebase Admin SDK initialized in src/lib/firebase.ts
    - [ ] TypeScript interfaces defined for predictions, performance, blog_metadata
    - [ ] Test write to Firestore confirms connection works
  - **Files touched:** `src/lib/firebase.ts`, `src/types/firestore.ts`, `package.json`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Follow architecture.md data model for collection structure. Use TypeScript strict typing for all Firestore operations.

- **T-006:** Configure Firestore security rules
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** T-005
  - **Acceptance Criteria (Task Level):**
    - [ ] Security rules set to allow client read-only access
    - [ ] Write access restricted to service account only
    - [ ] Rules tested and deployed to Firestore
  - **Files touched:** `firestore.rules`, Firestore console
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Client should only read, pipeline writes via service account. Test rules with Firebase emulator if available.

---

#### TS-016: Python ML pipeline project setup

> **As a** developer, **I need** to set up the Python pipeline project structure with dependencies and virtual environment **so that** ML development can begin

**Priority:** Must
**Story Points:** 2
**Depends on:** -
**Status:** Todo

**Acceptance Criteria (Story Level):**

- [ ] Python 3.11+ virtual environment created and activated
- [ ] All dependencies installed (XGBoost, Pandas, nba_api, pytest)
- [ ] Project structure follows architecture.md (pipeline/data, pipeline/model, pipeline/publish)
- [ ] Basic pytest test suite runs successfully

**Tasks:**

- **T-007:** Create Python virtual environment and install dependencies
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** -
  - **Acceptance Criteria (Task Level):**
    - [ ] Python 3.11+ virtual environment created in /pipeline
    - [ ] requirements.txt created with all dependencies
    - [ ] All packages install without errors
  - **Files touched:** `pipeline/requirements.txt`, `pipeline/.venv/`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Pin dependency versions. Include XGBoost, Pandas, nba_api, pytest, mypy. Use `python -m venv .venv`.

- **T-008:** Create pipeline folder structure and placeholder files
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** T-007
  - **Acceptance Criteria (Task Level):**
    - [ ] Folders created: pipeline/data, pipeline/model, pipeline/publish, pipeline/tests
    - [ ] Placeholder Python files created with docstrings
    - [ ] **init**.py files added for proper imports
  - **Files touched:** `pipeline/data/`, `pipeline/model/`, `pipeline/publish/`, `pipeline/tests/`, `pipeline/__init__.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Match architecture.md pipeline structure. Add type hints to all function signatures. Create basic README for pipeline.

- **T-009:** Configure pytest and mypy for Python testing
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** T-008
  - **Acceptance Criteria (Task Level):**
    - [ ] pytest.ini configured with test discovery settings
    - [ ] mypy.ini configured for type checking
    - [ ] Sample test created and passing
  - **Files touched:** `pipeline/pytest.ini`, `pipeline/mypy.ini`, `pipeline/tests/test_sample.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Enable strict type checking in mypy. Sample test should verify basic imports work.

---

#### TS-001: NBA Stats API data ingestion

> **As a** developer, **I need** to implement data ingestion from NBA Stats API via nba_api **so that** the model has fresh training data

**Priority:** Must
**Story Points:** 5
**Depends on:** TS-016
**Status:** Todo

**Acceptance Criteria (Story Level):**

- [ ] Script fetches team stats from NBA Stats API successfully
- [ ] Data saved to Parquet files with correct schema
- [ ] Rate limiting implemented with exponential backoff
- [ ] Error handling covers API failures and network issues
- [ ] Unit tests verify data structure and error handling

**Tasks:**

- **T-010:** Implement NBA API client wrapper with rate limiting
  - **Status:** Todo
  - **Complexity:** M
  - **Depends on:** -
  - **Acceptance Criteria (Task Level):**
    - [ ] Client wrapper uses nba_api library for all NBA API calls
    - [ ] Rate limiting enforces max 10 requests per minute
    - [ ] Exponential backoff retry logic (2s, 4s, 8s delays)
  - **Files touched:** `pipeline/data/nba_client.py`, `pipeline/tests/test_nba_client.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Follow tech-specs.md implementation example for retry logic. Test with real API but use mocks in tests.

- **T-011:** Implement team stats fetching for current season
  - **Status:** Todo
  - **Complexity:** M
  - **Depends on:** T-010
  - **Acceptance Criteria (Task Level):**
    - [ ] Function fetches all team stats for specified season
    - [ ] Data transformed into Pandas DataFrame with correct columns
    - [ ] Missing data handled with appropriate defaults or nulls
  - **Files touched:** `pipeline/data/fetch_team_stats.py`, `pipeline/tests/test_fetch_team_stats.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Include win rate, point differential, home/away splits, rest days per architecture.md feature list.

- **T-012:** Implement Parquet file storage for training data
  - **Status:** Todo
  - **Complexity:** S
  - **Depends on:** T-011
  - **Acceptance Criteria (Task Level):**
    - [ ] Data saved to Parquet files partitioned by season
    - [ ] Schema validation ensures consistent column types
    - [ ] Files compressed efficiently for storage
  - **Files touched:** `pipeline/data/storage.py`, `pipeline/tests/test_storage.py`, `pipeline/data/raw/`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Use Pandas to_parquet with snappy compression. Validate schema matches expected types before write.

---

#### TS-002: XGBoost model training pipeline

> **As a** developer, **I need** to implement feature engineering and XGBoost model training **so that** daily predictions are produced

**Priority:** Must
**Story Points:** 8
**Depends on:** SK-001, TS-001
**Status:** Todo

**Acceptance Criteria (Story Level):**

- [ ] Feature engineering creates model-ready dataset from raw stats
- [ ] XGBoost classifier trains successfully on historical data
- [ ] Model generates predictions with probability percentages
- [ ] Predictions written to Firestore with correct schema
- [ ] Model evaluation metrics (accuracy, precision, recall) logged

**Tasks:**

- **T-013:** Implement feature engineering pipeline
  - **Status:** Todo
  - **Complexity:** L
  - **Depends on:** -
  - **Acceptance Criteria (Task Level):**
    - [ ] Features created: rolling 10-game window, back-to-back detection, home/away splits
    - [ ] Feature set matches decision from SK-001 spike
    - [ ] Output DataFrame validated with correct column types
  - **Files touched:** `pipeline/model/feature_engineering.py`, `pipeline/tests/test_feature_engineering.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Use Pandas rolling windows for recent form features. Back-to-back detection based on game schedule timestamps.

- **T-014:** Implement XGBoost model training with cross-validation
  - **Status:** Todo
  - **Complexity:** L
  - **Depends on:** T-013
  - **Acceptance Criteria (Task Level):**
    - [ ] XGBoost classifier configured with hyperparameters from tech-specs.md
    - [ ] Time-series cross-validation implemented to prevent data leakage
    - [ ] Model evaluation metrics logged (accuracy, precision, recall, F1)
  - **Files touched:** `pipeline/model/train_model.py`, `pipeline/tests/test_train_model.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Use XGBoost parameters: n_estimators=100, max_depth=5, learning_rate=0.1 per tech-specs. Time-series CV prevents future data leakage.

- **T-015:** Implement prediction generation for today's games
  - **Status:** Todo
  - **Complexity:** M
  - **Depends on:** T-014
  - **Acceptance Criteria (Task Level):**
    - [ ] Predictions generated for all scheduled games today
    - [ ] Probability percentages calculated and confidence levels assigned
    - [ ] Output matches Firestore prediction schema exactly
  - **Files touched:** `pipeline/model/generate_predictions.py`, `pipeline/tests/test_generate_predictions.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Confidence thresholds: >65% = high, >55% = medium, <=55% = low per tech-specs.md.

- **T-016:** Implement Firestore write for predictions
  - **Status:** Todo
  - **Complexity:** M
  - **Depends on:** T-015
  - **Acceptance Criteria (Task Level):**
    - [ ] Predictions written to Firestore predictions collection
    - [ ] Schema validation ensures all required fields present
    - [ ] Error handling covers Firestore write failures with retry
  - **Files touched:** `pipeline/publish/firestore_writer.py`, `pipeline/tests/test_firestore_writer.py`
  - **QA loops:** 0/3
  - **Code Review loops:** 0/2
  - **Notes for Builder:** Use Firebase Admin SDK. Validate prediction schema before write. Implement retry on transient failures.

---

## Notes

**Sprint Focus:** This sprint establishes the foundational infrastructure for both web and ML components. Two spikes must complete first to inform technical decisions for TS-002. TS-012, TS-013, and TS-016 are independent and can be worked in parallel.

**Critical Path:** SK-001 → TS-001 → TS-002 is the longest dependency chain. SK-002 informs future pipeline automation but doesn't block this sprint.

**Velocity Assumption:** 23 points in 80 hours assumes ~3.5 hours per point. This is conservative for a first sprint with learning curve on NBA API and XGBoost.

**Risks:**

- NBA Stats API reliability (mitigation: aggressive caching, documented in architecture.md)
- XGBoost model accuracy target (mitigation: SK-001 spike validates approach before full implementation)
- Firebase free tier limits (mitigation: monitor usage, documented cost triggers in architecture.md)

**Definition of Done Reference:** All tasks must meet DoD criteria from `/home/emhar/avaris-ai/project/docs/governance/definition-of-done.md` including type checking, linting, tests, and code review.
