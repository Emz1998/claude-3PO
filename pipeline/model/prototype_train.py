"""XGBoost prototype training with feature combinations and SHAP analysis."""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score
import shap
from typing import Dict, List, Tuple

# Module constants
XGBOOST_PARAMS = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "tree_method": "hist",
    "objective": "binary:logistic",
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}

CV_N_SPLITS = 5
CV_GAP = 1
ROLLING_WINDOW = 10

COMBO_A_FEATURES = [
    "home_fg_pct_10g",
    "home_reb_10g",
    "home_ast_10g",
    "home_tov_10g",
    "home_win_pct_10g",
    "is_home",
]

COMBO_B_FEATURES = [
    "home_efg_pct_10g",
    "home_tov_pct_10g",
    "home_oreb_pct_10g",
    "home_ftr_10g",
    "opp_efg_pct_10g",
    "opp_tov_pct_10g",
    "opp_oreb_pct_10g",
    "opp_ftr_10g",
    "is_home",
]

COMBO_C_FEATURES = COMBO_B_FEATURES + [
    "home_net_rtg_10g",
    "home_ortg_10g",
    "home_rest_days",
    "home_3par_10g",
]


def make_game_rows(n: int, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic NBA game data for testing.

    Args:
        n: Number of game rows to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with n rows of synthetic game data
    """
    rng = np.random.default_rng(seed)

    # Generate synthetic features
    data = {
        "team_id": rng.integers(0, 30, n),
        "game_id": np.arange(n),
        "HOME_W": rng.integers(0, 2, n),  # Binary target
        "home_fg_pct": rng.uniform(0.40, 0.55, n),
        "home_reb": rng.integers(35, 55, n),
        "home_ast": rng.integers(20, 35, n),
        "home_tov": rng.integers(10, 20, n),
        "home_win_pct": rng.uniform(0.2, 0.8, n),
        "home_efg_pct": rng.uniform(0.45, 0.60, n),
        "home_tov_pct": rng.uniform(0.12, 0.20, n),
        "home_oreb_pct": rng.uniform(0.18, 0.35, n),
        "home_ftr": rng.uniform(0.15, 0.35, n),
        "opp_efg_pct": rng.uniform(0.45, 0.60, n),
        "opp_tov_pct": rng.uniform(0.12, 0.20, n),
        "opp_oreb_pct": rng.uniform(0.18, 0.35, n),
        "opp_ftr": rng.uniform(0.15, 0.35, n),
        "home_net_rtg": rng.uniform(-10, 10, n),
        "home_ortg": rng.uniform(100, 120, n),
        "home_rest_days": rng.integers(1, 5, n),
        "home_3par": rng.uniform(0.25, 0.40, n),
        "is_home": 1,
    }

    df = pd.DataFrame(data)
    return df


def add_rolling_features(df: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame:
    """Add rolling window features for XGBoost input.

    CRITICAL: Uses .shift(1).rolling() pattern to prevent temporal data leakage.
    The reference notebook omits shift(1), causing leakage.

    Args:
        df: Input DataFrame with base features
        window: Rolling window size (default 10 games)

    Returns:
        DataFrame with added rolling features
    """
    df = df.copy()

    # Define base features to create rolling versions
    base_features = [
        ("home_fg_pct", "home_fg_pct_10g"),
        ("home_reb", "home_reb_10g"),
        ("home_ast", "home_ast_10g"),
        ("home_tov", "home_tov_10g"),
        ("home_win_pct", "home_win_pct_10g"),
        ("home_efg_pct", "home_efg_pct_10g"),
        ("home_tov_pct", "home_tov_pct_10g"),
        ("home_oreb_pct", "home_oreb_pct_10g"),
        ("home_ftr", "home_ftr_10g"),
        ("opp_efg_pct", "opp_efg_pct_10g"),
        ("opp_tov_pct", "opp_tov_pct_10g"),
        ("opp_oreb_pct", "opp_oreb_pct_10g"),
        ("opp_ftr", "opp_ftr_10g"),
        ("home_net_rtg", "home_net_rtg_10g"),
        ("home_ortg", "home_ortg_10g"),
        ("home_3par", "home_3par_10g"),
    ]

    # Apply rolling features grouped by team
    for base_col, rolling_col in base_features:
        if base_col in df.columns:
            # shift(1) must precede rolling() — reference notebook omits this, causing leakage
            df[rolling_col] = df.groupby("team_id")[base_col].shift(1).rolling(window, min_periods=1).mean()

    return df


def train_combo(X: pd.DataFrame, y: pd.Series, combo: str) -> Dict:
    """Train XGBoost model with TimeSeriesSplit cross-validation.

    Args:
        X: Feature matrix
        y: Target vector
        combo: Feature combination name (A, B, or C)

    Returns:
        Dict with combo name, mean accuracy, std accuracy, feature importances, and model
    """
    # Remove rows with NaN values
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask].reset_index(drop=True)
    y = y[mask].reset_index(drop=True)

    # TimeSeriesSplit for temporal data
    tscv = TimeSeriesSplit(n_splits=CV_N_SPLITS, gap=CV_GAP)

    # Train with cross-validation
    model = xgb.XGBClassifier(**XGBOOST_PARAMS)

    cv_scores = []
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model.fit(X_train, y_train, verbose=False)
        y_pred = model.predict(X_test)
        score = accuracy_score(y_test, y_pred)
        cv_scores.append(score)

    cv_scores = np.array(cv_scores)

    # Train final model on all data for SHAP
    model.fit(X, y, verbose=False)

    # Get feature importances
    importances = model.get_booster().get_score(importance_type='weight')
    importance_list = [importances.get(f, 0) for f in X.columns]
    importance_list = np.array(importance_list) / (sum(importance_list) + 1e-8)

    return {
        "combo": combo,
        "mean_cv_accuracy": float(cv_scores.mean()),
        "std_cv_accuracy": float(cv_scores.std()),
        "feature_importances": importance_list,
        "model": model,
    }


def compute_shap_values(model, X: pd.DataFrame) -> np.ndarray:
    """Compute SHAP values for feature importance analysis.

    Args:
        model: Trained XGBoost model
        X: Feature matrix

    Returns:
        SHAP values array
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # Guard against list return (for certain model types)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    return np.array(shap_values)


def get_top_n_features(
    shap_values: np.ndarray, feature_names: List[str], n: int = 10
) -> List[Tuple[str, float]]:
    """Get top N features by mean absolute SHAP value.

    Args:
        shap_values: SHAP values array (n_samples, n_features)
        feature_names: List of feature names
        n: Number of top features to return

    Returns:
        List of (feature_name, importance) tuples sorted by importance descending
    """
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    # Create tuples of (feature_name, importance)
    feature_importance = list(zip(feature_names, mean_abs_shap))

    # Sort by importance descending
    feature_importance = sorted(feature_importance, key=lambda x: x[1], reverse=True)

    return feature_importance[:n]


def run_all_combos(df: pd.DataFrame) -> List[Dict]:
    """Run training for all 3 feature combinations.

    Args:
        df: Input DataFrame with all features

    Returns:
        List of results dicts for each combo
    """
    results = []

    # Combo A
    X_a = df[COMBO_A_FEATURES]
    y = df["HOME_W"]
    result_a = train_combo(X_a, y, "A")
    results.append(result_a)

    # Combo B
    X_b = df[COMBO_B_FEATURES]
    result_b = train_combo(X_b, y, "B")
    results.append(result_b)

    # Combo C
    X_c = df[COMBO_C_FEATURES]
    result_c = train_combo(X_c, y, "C")
    results.append(result_c)

    return results


def main():
    """CLI entry point: Run all combos, print comparison table and top-10 features."""
    print("Generating synthetic NBA game data...")
    df = make_game_rows(n=200, seed=42)

    print("Adding rolling features...")
    df = add_rolling_features(df)

    print("Training all feature combinations...")
    results = run_all_combos(df)

    # Print comparison table
    print("\n" + "=" * 80)
    print("FEATURE COMBINATION COMPARISON")
    print("=" * 80)
    print(f"{'Combo':<10} {'Features':<10} {'Mean Accuracy':<20} {'Std Accuracy':<15}")
    print("-" * 80)

    for result in results:
        combo = result["combo"]
        num_features = len(COMBO_A_FEATURES if combo == "A" else (COMBO_B_FEATURES if combo == "B" else COMBO_C_FEATURES))
        mean_acc = result["mean_cv_accuracy"]
        std_acc = result["std_cv_accuracy"]
        print(f"{combo:<10} {num_features:<10} {mean_acc:<20.4f} {std_acc:<15.4f}")

    # Compute SHAP and get top features
    print("\n" + "=" * 80)
    print("TOP-10 FEATURES BY SHAP IMPORTANCE")
    print("=" * 80)

    for result in results:
        combo = result["combo"]
        model = result["model"]

        if combo == "A":
            X = df[COMBO_A_FEATURES]
        elif combo == "B":
            X = df[COMBO_B_FEATURES]
        else:
            X = df[COMBO_C_FEATURES]

        # Remove rows with NaN
        mask = ~X.isna().any(axis=1)
        X = X[mask]

        shap_values = compute_shap_values(model, X)
        top_features = get_top_n_features(shap_values, X.columns.tolist(), n=10)

        print(f"\nCombo {combo}:")
        print(f"{'Rank':<6} {'Feature':<30} {'Importance':<15}")
        print("-" * 51)
        for rank, (feature, importance) in enumerate(top_features, 1):
            print(f"{rank:<6} {feature:<30} {importance:<15.6f}")


if __name__ == "__main__":
    main()
