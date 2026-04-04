# Avaris NBA ML Project — Codebase Status

**Project**: Avaris — ML-powered NBA game prediction website with daily moneyline picks  
**Version**: v0.1.0 (Sprint 1, Feb 17 - Mar 2, 2026)  
**Status**: Early-stage planning; no production ML code written yet  

---

## Project Structure

### Main Working Tree
**Location**: `/home/emhar/avaris-ai/.claude/worktrees/SPRINT-001/SK-002/project2/`

### Key Directories

| Path | Purpose | Status |
|---|---|---|
| `docs/architecture/` | Architecture docs, ADRs, coding standards | Complete |
| `docs/architecture/decisions.md` | 7 key ADRs (XGBoost, Next.js, Firebase, etc.) | Complete |
| `misc/specs/tech-specs.md` | Detailed technical specifications with code patterns | Complete |
| `.codex/skills/nba-data/` | NBA API reference docs and example Jupyter notebooks | Complete |
| `/pipeline/` | Planned Python ML pipeline structure (not created yet) | Planned |
| `/src/` | Planned Next.js frontend (not created yet) | Planned |

---

## Architecture & Technology Stack

**Backend (ML/Data)**
- Language: Python 3.10+
- ML Framework: XGBoost (binary classification for win/loss)
- Data Source: `nba_api` library (primary)
- Data Format: Parquet (for model training data)
- Infrastructure: GitHub Actions (cron-based nightly retraining)

**Frontend**
- Framework: Next.js 15 (App Router) + React 19
- Styling: Tailwind CSS v4
- Deployment: Vercel (free tier)

**Backend Infrastructure**
- Database: Firebase Firestore (predictions storage)
- Hosting: (TBD in Phase 2)

---

## Feature Engineering Reference

### Existing Reference Work

**Jupyter Notebook**: `/home/emhar/avaris-ai/.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling/Home Team Win-Loss Data Prep.ipynb`

This reference notebook provides complete feature engineering patterns:

| Feature | Type | Notes |
|---|---|---|
| `HOME/AWAY_LAST_GAME_OE` | Efficiency | Offensive efficiency with leakage bug (uses current game) |
| `HOME/AWAY_LAST_GAME_*_WIN_PCTG` | Cumulative | Home/away/total win percentages |
| `HOME/AWAY_LAST_GAME_ROLLING_SCORING_MARGIN` | Rolling Avg | 3-game window |
| `HOME/AWAY_LAST_GAME_ROLLING_OE` | Rolling Avg | 3-game offensive efficiency |
| `HOME/AWAY_NUM_REST_DAYS` | Context | Days since last game |

**Reference Model Performance** (Logistic Regression, 2022-23 validation):
- Test accuracy: 61.4%
- F1 macro: 0.61

**Known Issue**: The reference notebook has temporal leakage in rolling features — uses current game in rolling average. Must apply `.shift(1)` before rolling to fix.

---

## Research Findings: NBA Stats for XGBoost Prediction (SK-001)

### Top 10 Features Ranked by SHAP Importance (Cross-Study)

| Rank | Feature | Category | Expected Impact |
|------|---------|----------|----------------|
| 1 | eFG% differential (10g rolling) | Four Factors | High — adjusts for 3-point value; top SHAP in multiple studies |
| 2 | DRB% (10g rolling) | Four Factors | High — possession control; strongest single feature (PLOS One) |
| 3 | TOV% (10g rolling) | Four Factors | High — consistent top-4 SHAP at all game stages |
| 4 | Net Rating (10g rolling) | Advanced | High — encodes both ORTG+DRTG; best single-number team quality proxy |
| 5 | Win % (10g rolling) | Context | High — top pre-game predictor (Scientific Reports 2025) |
| 6 | Home/Away flag | Context | High — top-3 pre-game predictor; simple but consistent |
| 7 | ORTG differential (10g rolling) | Advanced | Medium — direct scoring efficiency signal |
| 8 | FTR (10g rolling) | Four Factors | Medium — aggression, foul drawing, late-game strategy |
| 9 | OREB% (10g rolling) | Four Factors | Medium — second-chance points; second-half predictor |
| 10 | 3PAr (10g rolling) | Style | Medium — offensive system indicator |

### Theoretical Foundation: Dean Oliver's Four Factors
Explain 96% of variance in team wins. Must implement both offensive and defensive versions:

| Factor | Formula | Oliver Weight |
|---|---|---|
| eFG% | (FG + 0.5 × 3P) / FGA | 40% |
| TOV% | TOV / (FGA + 0.44×FTA + TOV) | 25% |
| ORB% | ORB / (ORB + Opp DRB) | 20% |
| FTR | FTA / FGA | 15% |

### Feature Set Recommendations (3 Combinations for T-019)

| Set | Features | Pros | Cons | Expected Accuracy |
|-----|---------|------|------|------------------|
| **A (Basic)** | FG%, REB, AST, TOV, win_pct_10g, is_home | Simple, low pipeline complexity | No pace adjustment, ~65% ceiling | 63–67% |
| **B (Four Factors)** | eFG%, TOV%, OREB%, FTR + opponent versions + home | Theory-grounded, pace-adjusted | Requires box score aggregation | 67–70% |
| **C (Extended)** | Set B + NetRtg, ORTG, rest_days, 3PAr (all 10g rolling) | Highest accuracy, captures momentum and fatigue | More pipeline complexity, leakage risk if done wrong | 70–74% |

**Decision**: Use Feature Set C (Extended) as production feature set.

### Feature Engineering Best Practices
1. **Rolling Windows**: Test 5, 10, 15-game windows; 10 is typically optimal
2. **Temporal Safety**: Always `.shift(1)` before `.rolling()` — no exceptions
3. **Cross-Validation**: Use `TimeSeriesSplit(n_splits=5, gap=1)` — never random K-fold
4. **Feature Importance**: Use SHAP `TreeExplainer` (primary) + built-in `gain` (secondary sanity check)
5. **Leakage Audit**: Verify rolling features use only past games
6. **Sort first**: Sort by `GAME_DATE` before any split — never shuffle rows

### Feature Importance Method Comparison

| Method | Reliability | Notes |
|--------|-------------|-------|
| SHAP (TreeExplainer) | Best — gold standard | Handles correlated features fairly; theoretically grounded |
| Built-in `gain` | Good | Average loss reduction per split; use as secondary check |
| Built-in `weight` | Poor | Biased toward high-cardinality features; avoid as primary |
| Permutation importance | Good | Reliable for correlated features; computationally expensive |

---

## XGBoost Configuration (Planned)

**Baseline Hyperparameters** (from tech-specs.md):
```python
XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    objective='binary:logistic'
)
```

**Refined Hyperparameters** (from research):
```python
XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=1.0,
    early_stopping_rounds=20,
    tree_method="hist",
    objective="binary:logistic",
    eval_metric=["logloss", "auc"],
    random_state=42,
    n_jobs=-1,
)
```

**Accuracy Gate**: AUC > 0.72 required for deployment  
**Spike target**: AUC > 0.67 (prototype validation)

### Accuracy Benchmarks (from Literature)

| Feature Set | Typical Accuracy | Source |
|-------------|-----------------|--------|
| Basic stats only | 63–67% | Bryant University study |
| Advanced stats (Four Factors) | 67–70% | PLOS One XGBoost+SHAP |
| Combined + rolling averages | 69–72% | Scientific Reports 2025 |
| In-game (halftime data) | 75–80% | Various |

---

## NBA API Endpoints for SK-001

| Endpoint | Data | Use |
|----------|------|-----|
| `leaguegamelog.LeagueGameLog` | Season game logs, basic box scores | Load game data per season |
| `boxscorefourfactorsv2` | Pre-computed eFG%, TOV%, OREB%, FTR + opponent versions | Four Factors directly |
| `boxscoreadvancedv2` | ORTG, DRTG, Net Rating | Advanced metrics |
| `TeamGameLogs` | Modern replacement for deprecated `cumestatsteamgames` | Schedule + per-game stats |

---

## Current Project State

### ML Pipeline Code
- **Status**: Not created
- **Planned Structure**:
  - `pipeline/requirements.txt` — ML dependencies (T-007, SK-001 prerequisite)
  - `pipeline/tests/test_feature_combinations.py` — TDD tests for SK-001 (T-019)
  - `pipeline/model/prototype_train.py` — SK-001 prototype script (T-019)
  - `pipeline/data/nba_client.py` — NBA API wrapper (T-010, in progress)
  - `pipeline/data/fetch_team_stats.py` — Team stats fetching (T-011, backlog)
  - `pipeline/data/storage.py` — Parquet storage (T-012, backlog)
  - `pipeline/model/feature_engineering.py` — Feature engineering (T-013, planned)
  - `pipeline/model/train.py` — XGBoost training (T-014, planned)
  - `pipeline/model/generate_predictions.py` — Daily predictions (T-015, planned)
  - `pipeline/publish/firestore_writer.py` — Firestore publication (T-016, planned)

### Frontend Code
- **Status**: Not created
- **Framework**: Next.js 15 (TS-012, planned)

### Configuration & Dependencies
- **requirements.txt**: Not created (T-007)
- **Current venv**: Only `numpy` and `pyarrow` installed; missing `xgboost`, `pandas`, `scikit-learn`, `shap`, `nba_api`

### Tests
- **ML Tests**: None written
- **Test Infrastructure**: No pytest config for ML work

---

## Dependencies Needed

| Package | Version | Purpose |
|---|---|---|
| `xgboost` | 2.x | Model training |
| `scikit-learn` | 1.x | Preprocessing, metrics, TimeSeriesSplit |
| `pandas` | 2.x | Data manipulation |
| `numpy` | 2.x | Numerical operations (installed) |
| `shap` | 0.45+ | Feature importance analysis |
| `nba_api` | 1.4+ | NBA data fetching |
| `pytest` | 8.x | Testing framework |
| `pyarrow` | 22.x | Parquet support (installed) |

---

## Sprint & Task Status

**Sprint 1** (Feb 17 - Mar 2, 2026): All stories currently **Todo**

| ID | Story | Type | Status | Blocker |
|---|---|---|---|---|
| **SK-001** | **Which NBA stats features yield best XGBoost accuracy** | **Spike** | **In Progress** | Critical path (unlocks SK-002, TS-001, TS-002) |
| T-017 | Feature importance analysis documented | Task | In Progress | SK-001 |
| T-018 | Feature set recommendations with pros/cons | Task | In Progress | SK-001 |
| T-019 | Prototype training script tests 3 feature combos | Task | In Progress | SK-001 |
| TS-001 | NBA Stats API data ingestion | Story | Todo | SK-001 → TS-001 |
| TS-002 | XGBoost model training pipeline | Story | Todo | TS-001 |

---

## Acceptance Criteria (SK-001)

- Feature importance analysis completed and documented  
- Top 10 features identified and ranked by importance  
- Feature set recommendations provided with pros/cons  
- Expected accuracy impact assessed for each feature  

---

## References & Resources

- **NBA API Skill Docs**: `/home/emhar/avaris-ai/.codex/skills/nba-data/`
- **Data Prep Reference Notebook**: `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling/Home Team Win-Loss Data Prep.ipynb`
- **Modeling Reference Notebook**: `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling/Home Team Win-Loss Modeling.ipynb`
- **Tech Specs**: `.claude/worktrees/SPRINT-001/SK-002/project2/misc/specs/tech-specs.md`
- **Architectural Decisions**: `.claude/worktrees/SPRINT-001/SK-002/project2/docs/architecture/decisions.md`
- **PLOS One XGBoost+SHAP NBA study**: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0307478
- **Scientific Reports Stacked Ensemble 2025**: https://www.nature.com/articles/s41598-025-13657-1

---

**Last Updated**: 2026-04-02  
**Context**: SK-001 Spike — Feature importance analysis for NBA XGBoost model; research phase complete
