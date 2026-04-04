# Plan Quality Review: SK-001 NBA Feature Importance Analysis
## Iteration 2 Review

**Plan file:** `/home/emhar/avaris-ai/.claude/plans/snazzy-toasting-acorn.md`
**Reviewer:** Plan Quality Analyst
**Review date:** 2026-04-01
**Previous scores:** confidence=78, quality=82
**This iteration:** confidence=88, quality=87

---

## Executive Summary

The plan has been materially improved in iteration 2. All eight gaps identified in the prior review have been addressed with concrete, verifiable changes. The plan is now specific enough to implement without ambiguity, the leakage correction is clearly documented, the XGBoost 2.x API is correctly specified, and the test assertions are tightened. Two minor gaps remain: the synthetic DataFrame column schema for `run_spike()` diverges slightly from the reference notebook's actual column names, and the plan does not specify how `StratifiedKFold` CV interacts with the chronological `use_time_split=True` path. Neither gap blocks implementation, but both introduce test-writing ambiguity.

The plan meets approval threshold on both scores.

---

## Scores

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Confidence | 88/100 | Eight prior gaps resolved with precision. Two minor residual ambiguities remain (synthetic column schema alignment, CV / time-split interaction). Not enough uncertainty to fall below approval threshold. |
| Quality | 87/100 | Plan is well-structured, TDD sequence is correct, leakage correction is documented against the reference notebook, and acceptance criteria map cleanly to deliverables. Deducted points for synthetic schema misalignment and the missing interaction note between StratifiedKFold and time-split. |

---

## Resolved Gaps (Iteration 1 -> Iteration 2)

The following changes were confirmed by reading the updated plan text.

### 1. Leakage correction documented (plan section: Reference Files)
The plan now explicitly notes that `getRollingOE` in the reference notebook applies `.rolling(3, min_periods=1).mean()` without `.shift(1)`, and states this spike intentionally corrects that. This is accurate: the Data Prep notebook's `getRollingOE` function applies no shift, while `shiftGameLogRecords` in `getGameLogFeatureSet` applies a post-hoc shift on the already-computed rolling average — a pattern the plan replicates in `compute_rolling_avg`. The correction is technically sound and well-referenced.

### 2. Fixture size increased to 25 games per team-season (plan section: TDD Test Plan, conftest.py)
The fixture note now reads "must be >= 25 games per team-season to meaningfully exercise rolling windows at 5, 10, and 15." Window-15 requires at least 15 rows before `.shift(1)` produces a non-NaN result; 25 rows per group gives 10 non-NaN observations at window 15, which is sufficient for a meaningful rolling average assertion.

### 3. XGBoost 2.x API corrected (plan section: Implementation, train.py)
The constructor no longer contains `early_stopping_rounds`. The plan now correctly specifies `model.fit(..., callbacks=[xgb.callback.EarlyStopping(rounds=50)])`. The corresponding test assertion (`model.best_iteration` is set after fit) is a valid way to verify early stopping fired without mocking the internals.

### 4. Hardcoded accuracy estimates replaced with directional language (plan section: Feature Sets)
Combinations 2 and 3 now use "Expected to outperform baseline by 5-10+ AUC points" and "Expected to outperform advanced by 3-8 additional AUC points" rather than specific percentage figures. The only numeric gate is the AUC > 0.72 threshold in Verification.

### 5. Feature table replaced with [SPIKE OUTPUT] placeholders (plan section: decisions.md Structure)
The table now contains `[SPIKE OUTPUT]` placeholders for all 10 rows and both SHAP and Gain columns. This is correct for a spike: the table is a documentation template, not a pre-filled assertion.

### 6. run_spike() data source specified (plan section: Implementation, feature_comparison.py)
The plan now specifies: load `data/game_logs.csv` if it exists; otherwise generate a 500-row synthetic DataFrame with `numpy.random` and `random_state=42`. Column list is provided: TEAM_ID, SEASON, GAME_DATE, OFFENSIVE_EFFICIENCY, SCORING_MARGIN, WIN_PCTG, HOME_WIN_PCTG, AWAY_WIN_PCTG, NUM_REST_DAYS, HOME_FLAG, W.

### 7. test_stratified_kfold_used assertion clarified (plan section: test_train.py table)
The test now has a two-option assertion: inspect `cv_scores` list length == 5, or patch `StratifiedKFold` and assert it was called with `n_splits=5`. Both are valid; giving the implementer a choice is reasonable.

### 8. select_features() marked as forward-looking (plan section: Implementation, train.py)
The function is now annotated as "forward-looking utility, not exercised by spike entry point" and linked to TS-002. This prevents scope confusion during implementation.

---

## Remaining Gaps

### Gap A: Synthetic column schema partially misaligned with reference notebook (Minor)

**Plan location:** `run_spike()` description, `feature_comparison.py` section.

**Issue:** The plan's synthetic DataFrame column list includes `WIN_PCTG`, `HOME_WIN_PCTG`, `AWAY_WIN_PCTG`, and `W`. The reference Data Prep notebook generates `TOTAL_WIN_PCTG`, `HOME_WIN_PCTG`, `AWAY_WIN_PCTG`, and `W` (with `W` derived from cumulative wins). The plan's `WIN_PCTG` does not match `TOTAL_WIN_PCTG` used in `build_feature_set()` and the baseline column list (`TOTAL_WIN_PCTG_DIFF`).

More critically, the synthetic schema does not include columns that the advanced and comprehensive feature sets require: `FG_PCT`, `REB`, `AST`, `TOV`, `OFF_RATING`, `DEF_RATING`, `EFG_PCT`, `TS_PCT`, `TOV_RATE`, `THREE_PT_PCT`, `FT_RATE`, `NET_RATING`. The spike entry point runs `compare_feature_sets()` on this DataFrame, which calls `train_model()` with the advanced and comprehensive column lists. If those columns are absent from the synthetic DataFrame, the spike will either fail at runtime or produce meaningless results.

**Risk:** Medium — the spike run (step 10 of the Implementation Sequence) will likely raise a `KeyError` or produce all-NaN feature columns when the advanced and comprehensive sets are selected against a synthetic DataFrame that only has the minimal column list.

**Suggested resolution:** Extend the synthetic DataFrame schema in `run_spike()` to include all columns required by the comprehensive feature set, or add a note that the synthetic path only exercises the baseline feature set and the other two require `data/game_logs.csv`.

### Gap B: Interaction between StratifiedKFold and use_time_split=True is undefined (Minor)

**Plan location:** `train_model()` signature and `test_time_series_split_no_future_leakage` test.

**Issue:** The `train_model()` function signature includes `use_time_split=False`. The plan specifies `StratifiedKFold(n_splits=5)` CV and separately defines a `use_time_split=True` path that "enforces chronological order." It is unclear whether `use_time_split=True` replaces `StratifiedKFold` with `TimeSeriesSplit`, augments it, or is an entirely separate evaluation path. The test `test_time_series_split_no_future_leakage` asserts chronological order is enforced but does not specify how the implementer should detect that in the return dict.

**Risk:** Low — the implementer will likely resolve this with a reasonable choice, but two developers could make incompatible choices, creating a test that passes one implementation and fails the other.

**Suggested resolution:** Add one sentence to the `train_model()` description clarifying: when `use_time_split=True`, use `TimeSeriesSplit(n_splits=5)` instead of `StratifiedKFold`, and include the split type in the returned dict so the test can assert it.

---

## Strengths

**Strength 1: TDD sequence is correctly ordered and complete.**
The Implementation Sequence (section line 199-210) follows strict red-green order: fixtures and failing tests are written before any implementation module, and each `pytest` run is gated before the next implementation step. This is textbook TDD and matches the project's CLAUDE.md requirement.

**Strength 2: Leakage correction is grounded in the reference artifact.**
The plan cites the specific notebook function (`getRollingOE`), describes the exact missing operation (`.shift(1)`), and cross-references the correction in both the feature engineering description (`compute_rolling_avg`) and the test plan (`test_rolling_oe_uses_prior_games_only` / first row is NaN). This is the level of specificity needed for an implementer who has not read the notebook.

**Strength 3: Feature set column names are fully specified.**
All three feature set column lists are explicitly named in `get_feature_columns()`. This eliminates ambiguity in `test_get_feature_columns_baseline/advanced/comprehensive`, which must assert exact column lists. Without these definitions, those tests would have no ground truth.

**Strength 4: XGBoost API usage is verifiable.**
The plan specifies the exact callback class (`xgb.callback.EarlyStopping(rounds=50)`), the fit call signature, and a runtime-observable assertion (`model.best_iteration` is set). This is preferable to a mock-based approach because it validates the actual XGBoost behavior, not just that a call was made.

**Strength 5: decisions.md is a concrete, fillable artifact.**
The decisions.md structure defines both the table schema and the data source (`get_feature_importance(model, X, method="shap")`) that populates it. T-017 and T-018 have a clear output format, and the acceptance criteria mapping at the bottom of the Verification section is explicit.

**Strength 6: Accuracy gate is grounded in the reference baseline.**
The AUC > 0.72 gate is calibrated against the reference notebook's LogReg baseline (0.61 accuracy / F1 = 0.61), representing a meaningful improvement threshold rather than an arbitrary number. The reference notebook uses 12-fold CV on scaled data, which is a reasonable comparator.

---

## Technical Feasibility

**Architecture:** The three-module structure (`features.py`, `train.py`, `feature_comparison.py`) follows the single-responsibility principle and maps cleanly to the three child tasks. No circular imports are possible given the dependency direction: `feature_comparison` imports `train`, `train` imports `features`.

**Dependencies:** `xgboost`, `pandas`, `scikit-learn`, `shap` are all stable and available via `uv add`. SHAP's `TreeExplainer` is compatible with `XGBClassifier` as long as the model is trained with `objective="binary:logistic"`, which the plan specifies.

**Synthetic data path:** The 500-row synthetic DataFrame with `random_state=42` is sufficient to verify pipeline correctness for a spike, though model metrics will be meaningless on random data. This is acceptable for a research spike whose primary output is feature importance rankings on real data.

**Rolling window coverage:** 25 games per team-season with 5/10/15 windows and a `.shift(1)` means the first non-NaN value at window 15 appears at row index 15 (0-based). With 25 games, 10 rows per group will have full window-15 coverage. This is sufficient for the rolling window tests to be meaningful.

**CV strategy:** `StratifiedKFold(n_splits=5)` is appropriate for a binary classification task with potentially imbalanced home/away win rates. NBA home win rates are approximately 60-65%, which is mild enough that stratification is beneficial but not critical.

**SHAP compatibility note:** `shap.TreeExplainer(model).shap_values(X)` returns a 2D array for binary classification in older SHAP versions, but returns a list of arrays in some versions. The plan does not specify SHAP version pinning or how to handle the array shape. This is a low-risk implementation detail but worth noting.

---

## Acceptance Criteria Coverage

| AC | Plan Coverage | Evidence |
|----|--------------|---------|
| Feature importance analysis completed and documented | Full | decisions.md structure + `get_feature_importance()` spec + T-017 mapping |
| Top 10 features identified and ranked by importance | Full | `[SPIKE OUTPUT]` table with SHAP + Gain scores, `get_feature_importance(..., top_n=10)` |
| Feature set recommendations provided with pros/cons | Full | Feature Sets section + decisions.md recommendation table |
| Expected accuracy impact assessed for each feature | Partial | Directional language per set; individual feature-level accuracy impact is not quantified. AUC > 0.72 gate covers set-level impact only. |

The fourth AC ("expected accuracy impact assessed for each feature") is met at the feature-set level but not at the individual-feature level. SHAP values provide a ranking but not an accuracy-impact estimate per feature. This is acceptable for a spike — individual feature ablation studies are typically out of scope — but the implementer should be aware that "per feature" may be interpreted strictly during QA review.

---

## Summary of Changes Required Before Approval

The plan meets the 80/80 threshold and can proceed to implementation. The following non-blocking recommendations should be addressed before the Code Phase begins, or noted as known limitations in the spike output:

1. Extend the `run_spike()` synthetic DataFrame schema to include all columns needed by the advanced and comprehensive feature sets, or explicitly scope the synthetic path to baseline only.
2. Add one sentence to `train_model()` clarifying the `use_time_split=True` behavior and how the CV split type is surfaced in the return dict.

Neither item requires a plan revision cycle — they can be resolved in the conftest.py fixture or with a single implementation note.

