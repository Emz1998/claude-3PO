# SK-001: NBA Stats Feature Importance Analysis for XGBoost

## Context

This is a research spike to determine which NBA statistics yield the best XGBoost prediction accuracy. The deliverables unlock production pipeline stories TS-001 and TS-002. No production code will be written — all output is research artifacts and a prototype script. TDD is required: failing tests first, then minimal code to pass them.

---

## Approach

1. Create ML dependency file (`requirements.txt`) so packages can be installed
2. Write failing tests first (TDD) covering 3 feature combinations, SHAP importance, and data-leakage prevention
3. Implement a minimal prototype training script (`prototype_train.py`) that passes all tests — tests 3 feature combos with `TimeSeriesSplit` CV and SHAP feature importance
4. Document findings as DECISION-008 in the architecture decisions file, including top-10 features ranked, pros/cons of each feature set, and expected accuracy per combo

All rolling features must use `.shift(1).rolling()` (never `.rolling()` alone) to prevent temporal data leakage — the reference notebook has this bug and its 61.4% logistic regression baseline reflects partially leaked data.

---

## Files to Modify

| # | File | Action | Purpose |
|---|------|--------|---------|
| 1 | `pipeline/requirements.txt` | Create | ML dependencies |
| 2 | `pipeline/tests/__init__.py` | Create | Test package marker |
| 3 | `pipeline/model/__init__.py` | Create | Model package marker |
| 4 | `pipeline/tests/test_feature_combinations.py` | Create | TDD tests (failing first) |
| 5 | `pipeline/model/prototype_train.py` | Create | Prototype: 3 combos + SHAP |
| 6 | `.claude/worktrees/SPRINT-001/SK-002/project2/docs/architecture/decisions.md` | Append | DECISION-008 (T-017 + T-018) |

> All paths relative to `/home/emhar/avaris-ai/`

---

## Tasks

| ID | Description |
|----|-------------|
| T-017 | Feature importance analysis documented in decisions.md with top 10 features ranked |
| T-018 | Feature set recommendation with pros/cons and expected accuracy impact |
| T-019 | Prototype training script tests at least 3 different feature combinations |

---

## Implementation Steps

### Step 1 — Create requirements.txt

`pipeline/requirements.txt`:
```
xgboost>=2.0
scikit-learn>=1.4
pandas>=2.0
numpy>=2.0
shap>=0.45
nba_api>=1.4
pytest>=8.0
pytest-cov>=5.0
```

Install: `pip install -r pipeline/requirements.txt`

---

### Step 2 — Create Package Init Files

- `pipeline/tests/__init__.py` — `"""Tests for NBA XGBoost feature analysis."""`
- `pipeline/model/__init__.py` — `"""XGBoost model training and feature analysis for NBA predictions."""`

---

### Step 3 — Write Failing Tests (TDD)

File: `pipeline/tests/test_feature_combinations.py`

**4 test classes, all using `make_game_rows(n=200, seed=42)` synthetic data (no live API):**

**`TestSyntheticDataGeneration`**:
- `test_make_game_rows_returns_correct_shape` — returns DataFrame with 200 rows and all expected columns
- `test_make_game_rows_target_is_binary` — `HOME_W` contains only 0 and 1
- `test_no_data_leakage_in_rolling_features` — first row of rolling columns is NaN (shift applied)

**`TestFeatureCombinations`**:
- `test_combo_a_columns_exist_in_dataset` — all 6 Combo A feature columns present
- `test_combo_b_columns_exist_in_dataset` — all 9 Combo B feature columns present
- `test_combo_c_columns_exist_in_dataset` — all 13 Combo C feature columns present
- `test_feature_lists_do_not_contain_target` — `HOME_W` not in any combo's feature list

**`TestTrainWithCombos`**:
- `test_train_combo_a_returns_result_dict` — returns dict with keys `combo`, `mean_cv_accuracy`, `std_cv_accuracy`, `feature_importances`
- `test_train_combo_b_returns_result_dict`
- `test_train_combo_c_returns_result_dict`
- `test_cv_accuracy_is_between_zero_and_one` — `0 <= result["mean_cv_accuracy"] <= 1.0`
- `test_time_series_split_used` — mock-patches `TimeSeriesSplit`, asserts called with `n_splits=5, gap=1`

**`TestShapAnalysis`**:
- `test_shap_values_shape_matches_features` — SHAP array shape `(n_samples, n_features)` matches X
- `test_feature_importances_are_non_negative` — all mean |SHAP| values >= 0
- `test_top_n_features_returns_correct_count` — `get_top_n_features(..., n=10)` returns 10 tuples
- `test_top_n_features_sorted_descending` — sorted by importance descending

---

### Step 4 — Implement prototype_train.py (minimal to pass tests)

File: `pipeline/model/prototype_train.py`

**Module constants:**
```python
XGBOOST_PARAMS = {
    "n_estimators": 300, "max_depth": 4, "learning_rate": 0.05,
    "subsample": 0.8, "colsample_bytree": 0.8,
    "reg_alpha": 0.1, "reg_lambda": 1.0,
    "tree_method": "hist", "objective": "binary:logistic",
    "random_state": 42, "n_jobs": -1,
}
CV_N_SPLITS = 5
CV_GAP = 1
ROLLING_WINDOW = 10

COMBO_A_FEATURES = ["home_fg_pct_10g", "home_reb_10g", "home_ast_10g",
                    "home_tov_10g", "home_win_pct_10g", "is_home"]
COMBO_B_FEATURES = ["home_efg_pct_10g", "home_tov_pct_10g", "home_oreb_pct_10g",
                    "home_ftr_10g", "opp_efg_pct_10g", "opp_tov_pct_10g",
                    "opp_oreb_pct_10g", "opp_ftr_10g", "is_home"]
COMBO_C_FEATURES = COMBO_B_FEATURES + ["home_net_rtg_10g", "home_ortg_10g",
                                         "home_rest_days", "home_3par_10g"]
```

**Public functions (all with type hints):**

1. `make_game_rows(n: int, seed: int = 42) -> pd.DataFrame` — synthetic data using `numpy.random.default_rng(seed)`
2. `add_rolling_features(df: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame`
   - **Mandatory pattern**: `.shift(1).rolling(window, min_periods=1).mean()` grouped by `team_id`
   - Comment: `# shift(1) must precede rolling() — reference notebook omits this, causing leakage`
3. `train_combo(X: pd.DataFrame, y: pd.Series, combo: str) -> dict` — `TimeSeriesSplit(n_splits=5, gap=1)` CV, returns `{combo, mean_cv_accuracy, std_cv_accuracy, feature_importances}`
4. `compute_shap_values(model, X: pd.DataFrame) -> np.ndarray` — `shap.TreeExplainer(model).shap_values(X)` with list-return guard
5. `get_top_n_features(shap_values, feature_names, n=10) -> list[tuple[str, float]]` — mean |SHAP| descending, top n
6. `run_all_combos(df: pd.DataFrame) -> list[dict]` — orchestrates all 3 combos
7. `main()` — CLI: runs combos, prints comparison table + top-10 features

**Known risks and mitigations:**
- `early_stopping_rounds` needs eval_set: omit from CV; use only in final full-data fit
- SHAP list return: `if isinstance(shap_values, list): shap_values = shap_values[1]`

---

### Step 5 — Append DECISION-008 to decisions.md (T-017 + T-018)

Append after last `---` separator in `.claude/worktrees/SPRINT-001/SK-002/project2/docs/architecture/decisions.md`.

**Top 10 features (ranked by cross-study SHAP importance)**:

| Rank | Feature | Category | Expected Impact |
|------|---------|----------|----------------|
| 1 | eFG% differential (10g rolling) | Four Factors | High |
| 2 | DRB% (10g rolling) | Four Factors | High |
| 3 | TOV% (10g rolling) | Four Factors | High |
| 4 | Net Rating (10g rolling) | Advanced | High |
| 5 | Win % (10g rolling) | Context | High |
| 6 | Home/Away flag | Context | High |
| 7 | ORTG differential (10g rolling) | Advanced | Medium |
| 8 | FTR (10g rolling) | Four Factors | Medium |
| 9 | OREB% (10g rolling) | Four Factors | Medium |
| 10 | 3PAr (10g rolling) | Style | Medium |

**Feature set comparison**:

| Set | Features | Pros | Cons | Expected Accuracy |
|-----|---------|------|------|------------------|
| A (Basic) | 6 features | Simple, low complexity | No pace adjustment | 63–67% |
| B (Four Factors) | 9 features | Theory-grounded, pace-adjusted | Needs box score aggregation | 67–70% |
| C (Extended) | 13 features | Highest accuracy, momentum + fatigue | More complex pipeline | 70–74% |

Decision: Use Combo C as production feature set. AUC target > 0.72.

---

## Verification

1. `pip install -r pipeline/requirements.txt` — all deps install cleanly
2. `pytest pipeline/tests/test_feature_combinations.py -v` — all 16 tests pass
3. `python pipeline/model/prototype_train.py` — prints comparison table + top-10 features
4. Confirm `DECISION-008` appended in decisions.md with ranked features and pros/cons table

---

## Patterns to Reuse

- **`.shift(1).rolling()`** — from reference Data Prep notebook (with leakage bug fixed)
- **Season holdout split** — from reference Modeling notebook (`SEASON == '2022-23'` as validation)
- **pytest class structure** — from `.claude/hooks/workflow/tests/test_state_store.py`
- **`decisions.md` ADR format** — match existing DECISION-001..007 header/body format exactly
