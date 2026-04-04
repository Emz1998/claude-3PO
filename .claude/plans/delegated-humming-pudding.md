# SK-001: Which NBA Stats Features Yield Best XGBoost Accuracy

## Context

Research spike to identify which NBA game statistics features provide the best XGBoost classification accuracy for predicting home team wins. This unblocks TS-002 (XGBoost training pipeline). No ML code exists yet. A reference Jupyter notebook at `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling/` establishes a LogReg baseline (~61% accuracy). The spike must beat this baseline (target AUC > 0.72) and document findings in `decisions.md`.

TDD = True: failing tests written first, then minimal code to pass them.

---

## Approach

1. Install ML dependencies via `uv add xgboost pandas scikit-learn shap nba_api`
2. Scaffold `ml/` package with `__init__.py` files
3. Write failing TDD tests (`conftest.py` → `test_features.py` → `test_train.py`) — confirm all fail cleanly
4. Implement `ml/features.py` (leakage-safe rolling averages, differential features) → tests green
5. Implement `ml/train.py` (XGBClassifier + TimeSeriesSplit CV + SHAP importance) → tests green
6. Implement `ml/feature_comparison.py` (spike runner comparing 3 feature sets)
7. Run spike (`python -m ml.feature_comparison`) to collect actual AUC/F1 results
8. Write `decisions.md` at project root with spike output (top 10 features + recommendations)

---

## Files to Modify

**New files to create:**
- `ml/__init__.py`
- `ml/features.py` — feature computation, rolling averages, differencing
- `ml/train.py` — XGBClassifier training, TimeSeriesSplit CV, SHAP importance
- `ml/feature_comparison.py` — 3-combination comparison runner
- `ml/tests/__init__.py`
- `ml/tests/conftest.py` — shared fixtures (synthetic DataFrame, no NBA API)
- `ml/tests/test_features.py` — 11 TDD tests for features (written first)
- `ml/tests/test_train.py` — 6 TDD tests for training (written first)
- `decisions.md` — final deliverable at project root

**Reference files (read-only):**
- `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling/Home Team Win-Loss Data Prep.ipynb`
- `.codex/skills/nba-data/docs/examples/Home Team Win-Loss Modeling/Home Team Win-Loss Modeling.ipynb`

---

## Three Feature Sets (T-019)

| Set | Key Features | Count | Expected AUC |
|-----|-------------|-------|--------------|
| **Baseline** | WIN_PCTG_DIFF, FG_PCT_DIFF, REB_DIFF, AST_DIFF, TOV_DIFF, REST_DAYS_DIFF, HOME_INDICATOR, back-to-back flags | ~8 | 0.63–0.66 |
| **Advanced** | Baseline + EFG_PCT_DIFF, DRTG_DIFF, ORTG_DIFF, FG3_PCT_DIFF, FTR_DIFF, TOV_RATE_DIFF | ~15 | 0.68–0.71 |
| **Comprehensive** | Advanced + NET_RATING_DIFF, ROLL_EFG_PCT_5/10_DIFF, WIN_STREAK_DIFF | ~23 | 0.72–0.76 |

---

## TDD Test Specifications

### `ml/tests/conftest.py`
Single session-scoped fixture `game_log_df`: 500-row synthetic DataFrame with `random_state=42`. Mirrors `LeagueGameFinder` schema (GAME_ID, GAME_DATE, TEAM_ID, WL, FG_PCT, FG3_PCT, FT_PCT, REB, AST, TOV, FGA, FTA, OREB, DREB, PTS, PLUS_MINUS, SEASON_ID). Never calls the NBA API.

### `ml/tests/test_features.py` — written before `features.py`

| Test | Assertion |
|------|-----------|
| `test_rolling_columns_exist` | ROLL_FG_PCT_5 and ROLL_FG_PCT_10 in output |
| `test_no_data_leakage_rolling` | First row per team has NaN rolling avg (shift(1) applied) |
| `test_no_data_leakage_win_pct` | First row per team has NaN WIN_PCTG |
| `test_eFG_pct_formula` | EFG_PCT column exists |
| `test_tov_rate_formula` | TOV_RATE column exists |
| `test_rest_days_non_negative` | REST_DAYS ≥ 0 for all non-NaN rows |
| `test_back_to_back_is_binary` | BACK_TO_BACK values ∈ {0, 1} |
| `test_differential_columns_exist` | WIN_PCTG_DIFF, EFG_PCT_DIFF, DREB_DIFF present |
| `test_home_indicator_present` | HOME_INDICATOR ∈ {0, 1} |
| `test_target_column_present` | HOME_WIN ∈ {0, 1} |
| `test_raw_stats_dropped` | FG_PCT (raw same-game) NOT in game-level output |

### `ml/tests/test_train.py` — written before `train.py`

| Test | Assertion |
|------|-----------|
| `test_returns_metrics_dict` | Returns dict with keys: auc, accuracy, f1 |
| `test_auc_is_float_in_range` | 0.0 ≤ auc ≤ 1.0 |
| `test_shap_values_shape` | shap_values.shape == (n_samples, n_features) |
| `test_feature_sets_constant_defined` | FEATURE_SETS has baseline, advanced, comprehensive |
| `test_uses_time_series_split` | KFold is NOT called (monkeypatch assert) |
| `test_xgb_objective_binary_logistic` | objective == "binary:logistic" |

---

## Implementation Details

### `ml/features.py`

**`build_team_features(raw_df: pd.DataFrame) -> pd.DataFrame`**
Adds rolling and cumulative features per team. Drops raw same-game stat columns from output.

Core leakage guard pattern — used in every rolling computation:
```python
df.groupby(["TEAM_ID", "SEASON_ID"])["STAT"]
  .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
```
`.shift(1)` MUST precede `.rolling()`. Windows: 5 and 10. Stats: FG_PCT, FG3_PCT, EFG_PCT, TOV_RATE, ORTG, DRTG, NET_RATING.

Advanced stats formulas:
- `EFG_PCT = (FGM + 0.5 * FG3M) / FGA`
- `TOV_RATE = TOV / (FGA + 0.44 * FTA + TOV)`
- `FTR = FTA / FGA`

**`build_game_features(team_df: pd.DataFrame) -> pd.DataFrame`**
Joins home/away rows on GAME_ID. Returns one row per game with `*_DIFF` columns (home − away), HOME_INDICATOR, HOME_WIN target, GAME_DATE.

### `ml/train.py`

**`FEATURE_SETS: dict[str, list[str]]`** — constant defining the 3 column lists.

**`run_model(game_df, feature_set="baseline", return_shap=False) -> dict`**
```python
XGBClassifier(
    objective="binary:logistic",
    max_depth=6,
    n_estimators=300,
    eval_metric="logloss",
    random_state=42
)
model.fit(X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[xgb.callback.EarlyStopping(rounds=50)]  # XGBoost 2.x API
)
```
- CV: `TimeSeriesSplit(n_splits=5)` always — never `KFold`
- SHAP: `shap.TreeExplainer(model).shap_values(X_test)` on last fold if `return_shap=True`
- Returns: `{"auc", "accuracy", "f1", "feature_importances", "shap_values"}`

### `ml/feature_comparison.py`

- `run_spike(game_df)` — calls `run_model()` for all 3 sets, prints ranked AUC table
- `fetch_real_data(seasons=None)` — `LeagueGameFinder` with `time.sleep(0.6)` rate limiting, falls back to synthetic on exception
- Entry point: `python -m ml.feature_comparison [--synthetic]`

### `decisions.md`

Documents T-017 + T-018:
1. Top 10 features ranked by SHAP from comprehensive model (with AUC impact estimates)
2. Three feature sets: AUC results, pros/cons, recommendation
3. Known issues fixed (leakage in reference notebook)
4. Prototype results filled after `run_spike()` on real data

---

## Critical Technical Constraints

1. **Leakage prevention**: `shift(1)` before `.rolling()` in every groupby transform — mandatory
2. **No KFold**: `TimeSeriesSplit(n_splits=5)` always — temporal ordering required
3. **No NBA API in tests**: `conftest.py` synthetic fixture is the only test data source
4. **Feature drop discipline**: `features.py` drops raw same-game stats from output DataFrame
5. **Differential features**: All model features are `home − away` — halves feature count

---

## Verification

```bash
# All unit tests pass
pytest ml/tests/ -v --tb=short

# Leakage tests specifically
pytest ml/tests/test_features.py -k "leakage" -v

# Pipeline smoke test (synthetic, no network)
python -m ml.feature_comparison --synthetic

# Real data run (requires network)
python -m ml.feature_comparison
```

**Accuracy gate**: Comprehensive model AUC > 0.72 on real data (3 seasons, ~3,700 games).

**Acceptance criteria mapping:**
- T-017: `decisions.md` top 10 ranked features ← spike output
- T-018: `decisions.md` feature set recommendations with pros/cons ← spike output
- T-019: `compare_feature_sets()` tests 3 combinations ← `feature_comparison.py`
