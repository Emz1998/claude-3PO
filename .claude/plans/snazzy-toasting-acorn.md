# SK-001: NBA Feature Importance Analysis for XGBoost

## Context

Research spike to determine which NBA game statistics features yield the best XGBoost classification accuracy for predicting home team wins. No ML code exists yet in the project. A reference Jupyter notebook establishes a LogReg baseline (~61% accuracy) with a basic feature set. This spike identifies the top 10 features, tests 3 feature combinations, and documents findings in `decisions.md` to unblock TS-002 (XGBoost training pipeline).

TDD = True: tests must be written first (failing), then implementation.

---

## Directory Structure

```
ml/
├── __init__.py
├── features.py              # Feature computation + leakage-safe rolling averages
├── train.py                 # XGBClassifier + 5-fold CV + feature importance
├── feature_comparison.py    # Compare 3 feature set combinations, emit report
└── tests/
    ├── __init__.py
    ├── conftest.py          # Shared fixtures: synthetic DataFrames
    ├── test_features.py     # TDD tests for feature computation (written first)
    └── test_train.py        # TDD tests for training pipeline (written first)

decisions.md                 # Project root: top 10 features, pros/cons, accuracy impact
```

---

## Dependencies

Install via uv (only shell command needed):
```
uv add xgboost pandas scikit-learn shap
```

---

## Reference Files

- `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Data Prep.ipynb` — existing feature engineering patterns (rolling OE, win %, rest days)
- `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling.ipynb` — baseline LogReg (~61% accuracy, 12-fold CV)

**Important deviation from reference notebook:** The notebook's `getRollingOE` applies `.rolling(3, min_periods=1).mean()` without a `.shift(1)`, which includes the current game's OE in the rolling mean — a subtle data leakage. This plan intentionally corrects that by applying `.shift(1)` after every rolling computation, ensuring only prior games inform each row's features.

---

## Feature Sets (3 Combinations for T-019)

### Combination 1 — Baseline
Raw differentials: win % (total/home/away), FG%, rebounds, assists, turnovers, rest days.
Pros: simple, low data requirements | Cons: expected to fall below or near LogReg ceiling

### Combination 2 — Advanced
Baseline + offensive/defensive rating, eFG%, true shooting %, turnover rate, 3P%, free throw rate.
Pros: efficiency metrics capture possession quality, more interpretable | Cons: requires advanced stats feed
Expected to outperform baseline by 5-10+ AUC points.

### Combination 3 — Comprehensive
Advanced + net rating differential, rolling OE (5/10/15-game windows), back-to-back flag, home/away rest days.
Pros: best expected performance, captures fatigue/schedule/form | Cons: more complex data pipeline
Expected to outperform advanced by 3-8 additional AUC points.

*(Actual numeric results come from the spike run. See Verification section for the only numeric gate.)*

---

## TDD Test Plan

### `ml/tests/conftest.py`
Fixtures: `minimal_game_df` (synthetic game log, 100 rows, 2 teams × 2 seasons × 25 games — must be ≥25 games per team-season to meaningfully exercise rolling windows at 5, 10, and 15), `minimal_model_df` (pre-merged HOME_/AWAY_ prefixed columns), `feature_sets` (dict of 3 named feature column lists).

### `ml/tests/test_features.py` — Written FIRST (failing)

| Test | Assertion |
|------|-----------|
| `test_rolling_oe_uses_prior_games_only` | Rolling OE for game N uses games 0..N-1 (`.shift(1)`); first row is NaN |
| `test_rolling_average_window_5` | `compute_rolling_avg(..., window=5)` matches manual pandas calculation |
| `test_rolling_average_window_10` | Same for window=10 |
| `test_rolling_average_window_15` | Same for window=15 |
| `test_no_data_leakage` | After `build_feature_set()`, no row N value contains that game's own stats |
| `test_rest_days_computed_correctly` | `compute_rest_days()` returns correct day differences per team |
| `test_back_to_back_flag` | `compute_back_to_back()` returns 1 when rest_days==1, else 0 |
| `test_net_rating_differential` | `compute_differentials()` produces `NET_RATING_DIFF = HOME - AWAY` |
| `test_feature_differencing_reduces_columns` | `use_differencing=True` yields fewer columns than False |
| `test_get_feature_columns_baseline` | Returns exact documented baseline column list |
| `test_get_feature_columns_advanced` | Returns exact documented advanced column list |
| `test_get_feature_columns_comprehensive` | Returns exact documented comprehensive column list |
| `test_invalid_feature_set_name_raises` | `get_feature_columns("nonexistent")` raises `ValueError` |

### `ml/tests/test_train.py` — Written FIRST (failing)

| Test | Assertion |
|------|-----------|
| `test_train_returns_model_and_metrics` | Returns dict with keys: `model`, `auc`, `f1`, `accuracy` |
| `test_auc_is_float_between_0_and_1` | `auc` in [0.0, 1.0] |
| `test_f1_is_float_between_0_and_1` | `f1` in [0.0, 1.0] |
| `test_model_is_xgb_classifier` | `model` is `XGBClassifier` instance |
| `test_stratified_kfold_used` | 5-fold stratified CV is used — verify by inspecting `cv_scores` list length == 5 in returned metrics, or by patching `StratifiedKFold` and asserting it was called with `n_splits=5` |
| `test_compare_feature_sets_returns_three_results` | Returns dict with keys: `baseline`, `advanced`, `comprehensive` |
| `test_compare_results_have_required_keys` | Each sub-dict has: `auc`, `f1`, `accuracy`, `top_features` |
| `test_feature_importance_returns_top_10` | `get_feature_importance(..., method="gain")` returns 10 sorted `(name, score)` tuples |
| `test_shap_importance_returns_top_10` | `get_feature_importance(..., method="shap")` returns 10 sorted tuples via SHAP |
| `test_select_from_model_reduces_features` | `select_features()` returns DataFrame with fewer columns |
| `test_time_series_split_no_future_leakage` | `use_time_split=True` enforces chronological order |
| `test_xgb_objective_is_binary_logistic` | Model `objective` is `"binary:logistic"` |
| `test_early_stopping_configured` | Early stopping is active: verify `model.best_iteration` is set after `fit()`, confirming early stopping fired (XGBoost 2.x uses `early_stopping_rounds` in `fit()` callback, not the constructor) |

---

## Implementation

### `ml/features.py`

**`get_feature_columns(feature_set: str) -> list[str]`**
Returns column list for `"baseline"`, `"advanced"`, or `"comprehensive"`. Raises `ValueError` for unknown names.

Column definitions:
- `baseline`: `["HOME_WIN_PCTG_DIFF", "AWAY_WIN_PCTG_DIFF", "TOTAL_WIN_PCTG_DIFF", "FG_PCT_DIFF", "REB_DIFF", "AST_DIFF", "TOV_DIFF", "REST_DAYS_DIFF"]`
- `advanced`: baseline + `["OFF_RATING_DIFF", "DEF_RATING_DIFF", "EFG_PCT_DIFF", "TS_PCT_DIFF", "TOV_RATE_DIFF", "THREE_PT_PCT_DIFF", "FT_RATE_DIFF"]`
- `comprehensive`: advanced + `["NET_RATING_DIFF", "ROLLING_OE_5_DIFF", "ROLLING_OE_10_DIFF", "ROLLING_OE_15_DIFF", "HOME_BACK_TO_BACK", "AWAY_BACK_TO_BACK", "HOME_REST_DAYS", "AWAY_REST_DAYS"]`

**`compute_rolling_avg(df, col, window, group_cols=["TEAM_ID","SEASON"]) -> pd.Series`**
Groups by `group_cols`, sorts by `GAME_DATE`, applies `.rolling(window, min_periods=1).mean().shift(1)` — matching notebook's leakage guard pattern.

**`compute_rest_days(df) -> pd.Series`**
Groups by `["TEAM_ID","SEASON"]`, sorts by `GAME_DATE`, shifts date by 1, computes day difference. Matches notebook `getRestDays` logic.

**`compute_back_to_back(df) -> pd.Series`**
Returns `(compute_rest_days(df) == 1).astype(int)`.

**`compute_differentials(home_df, away_df, cols) -> pd.DataFrame`**
For each col: `home_val - away_val`. Reduces correlated home/away pairs to single differential.

**`build_feature_set(game_log_df, feature_set) -> pd.DataFrame`**
Orchestrates: rolling averages (5/10/15 windows), shift by 1 game, merge home/away frames, apply differencing. Returns DataFrame with `HOME_W` target + feature columns for named set.

### `ml/train.py`

**`train_model(X, y, feature_set="baseline", use_time_split=False) -> dict`**
- `XGBClassifier(objective="binary:logistic", max_depth=6, n_estimators=300, eval_metric="logloss", random_state=42)`
- Eval set: last 20% chronologically. Pass `early_stopping_rounds=50` to `fit()` via the `callbacks` parameter (XGBoost 2.x API — not the constructor): `model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[xgb.callback.EarlyStopping(rounds=50)])`
- CV strategy: `use_time_split=False` → `StratifiedKFold(n_splits=5)`; `use_time_split=True` → `TimeSeriesSplit(n_splits=5)` (replaces StratifiedKFold, enforces chronological order)
- Return `cv_scores` list (length 5) in result for test verifiability
- Returns `{"model", "auc", "f1", "accuracy", "top_features", "cv_scores"}`

**`get_feature_importance(model, X, method="gain") -> list[tuple]`**
- `"gain"`: `model.get_booster().get_score(importance_type="gain")`, top 10 sorted desc
- `"shap"`: `shap.TreeExplainer(model).shap_values(X)`, mean abs SHAP, top 10

**`select_features(model, X, threshold="mean") -> pd.DataFrame`** *(forward-looking utility, not exercised by spike entry point)*
Wraps `sklearn.feature_selection.SelectFromModel`. Returns X with only selected columns. Included for downstream TS-002 use; covered by `test_select_from_model_reduces_features`.

### `ml/feature_comparison.py`

**`compare_feature_sets(df) -> dict`**
Runs `train_model()` for all 3 feature sets, returns results dict.

**`print_comparison_report(results) -> None`**
Formatted table: AUC/F1/Accuracy per set + top 10 features from best set.

**`run_spike() -> None`**
Entry point (`python -m ml.feature_comparison`). Loads data from `data/game_logs.csv` if it exists; otherwise generates a 500-row synthetic DataFrame with all required columns using `numpy.random` with `random_state=42` for reproducibility. No live NBA API calls needed for the spike.

Synthetic schema must cover all three feature set levels:
`TEAM_ID, SEASON, GAME_DATE, OFFENSIVE_EFFICIENCY, SCORING_MARGIN, WIN_PCTG, HOME_WIN_PCTG, AWAY_WIN_PCTG, NUM_REST_DAYS, HOME_FLAG, W, FG_PCT, OFF_RATING, DEF_RATING, EFG_PCT, TS_PCT, TOV_RATE, THREE_PT_PCT, FT_RATE, NET_RATING`

---

## `decisions.md` Structure (T-017 + T-018)

### Top 10 Features Ranked (by SHAP from comprehensive model)

*[TO BE FILLED FROM SPIKE RUN — `get_feature_importance(model, X, method="shap")` output]*

| Rank | Feature | SHAP Score | Gain Score | Notes |
|------|---------|-----------|-----------|-------|
| 1 | [SPIKE OUTPUT] | | | |
| 2 | [SPIKE OUTPUT] | | | |
| 3 | [SPIKE OUTPUT] | | | |
| 4 | [SPIKE OUTPUT] | | | |
| 5 | [SPIKE OUTPUT] | | | |
| 6 | [SPIKE OUTPUT] | | | |
| 7 | [SPIKE OUTPUT] | | | |
| 8 | [SPIKE OUTPUT] | | | |
| 9 | [SPIKE OUTPUT] | | | |
| 10 | [SPIKE OUTPUT] | | | |

### Feature Set Recommendations

| Feature Set | AUC (spike result) | Pros | Cons |
|-------------|-------------------|------|------|
| Baseline | [SPIKE OUTPUT] | Simple, low data requirements | Expected near/below LogReg ceiling |
| Advanced | [SPIKE OUTPUT] | Efficiency metrics, interpretable | Requires advanced stats feed |
| Comprehensive | [SPIKE OUTPUT] | Best expected performance | More complex data pipeline |

**Recommendation:** Comprehensive set with SHAP-driven pruning to top 15 features via `SelectFromModel`.

---

## Approach

1. Install ML dependencies via `uv add xgboost pandas scikit-learn shap`
2. Scaffold `ml/` package with `__init__.py` files
3. Write failing TDD tests (`conftest.py` → `test_features.py` → `test_train.py`) — confirm all fail cleanly
4. Implement `ml/features.py` (feature computation + leakage-safe rolling averages) → tests green
5. Implement `ml/train.py` (XGBClassifier + 5-fold CV + SHAP importance) → tests green
6. Implement `ml/feature_comparison.py` (spike runner comparing 3 feature sets)
7. Run spike (`python -m ml.feature_comparison`) to collect actual AUC/F1 results
8. Write `decisions.md` at project root with spike output (top 10 features + recommendations)

## Critical Files

**New files to create:**
- `ml/__init__.py`
- `ml/features.py` — feature computation, rolling averages, differencing
- `ml/train.py` — XGBClassifier training, CV, SHAP importance, SelectFromModel
- `ml/feature_comparison.py` — 3-combination comparison runner
- `ml/tests/__init__.py`
- `ml/tests/conftest.py` — shared fixtures (≥25 games per team-season)
- `ml/tests/test_features.py` — 13 TDD tests for features (written first)
- `ml/tests/test_train.py` — 13 TDD tests for training (written first)
- `decisions.md` — final deliverable at project root

**Reference files (read-only):**
- `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Data Prep.ipynb`
- `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling.ipynb`

## Steps

1. `uv add xgboost pandas scikit-learn shap`
2. Create `ml/__init__.py`, `ml/tests/__init__.py`
3. Write `ml/tests/conftest.py` (fixtures only, no `ml/` imports)
4. Write `ml/tests/test_features.py` (failing)
5. Write `ml/tests/test_train.py` (failing)
6. Run `pytest ml/tests/ -v` — confirm all fail cleanly
7. Implement `ml/features.py` → run `pytest ml/tests/test_features.py` → green
8. Implement `ml/train.py` → run `pytest ml/tests/test_train.py` → green
9. Implement `ml/feature_comparison.py`
10. Run `python -m ml.feature_comparison` → collect results
11. Write `decisions.md` with actual numeric results

---

## Verification

```bash
# All tests pass
pytest ml/tests/ -v --tb=short

# Spike produces comparison report
python -m ml.feature_comparison

# Specific data leakage check
pytest ml/tests/test_features.py::TestRollingFeatures::test_no_data_leakage -v
```

**Accuracy gate:** Comprehensive model AUC > 0.72 (above LogReg baseline of ~0.61).

**Acceptance criteria mapping:**
- T-017: `decisions.md` top 10 ranked features ← spike output
- T-018: `decisions.md` feature set recommendations ← spike output  
- T-019: `compare_feature_sets()` tests all 3 combinations ← `feature_comparison.py`
