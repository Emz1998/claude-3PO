"""Parquet storage for NBA game data."""

from pathlib import Path

import pandas as pd


def save_to_parquet(df: pd.DataFrame, output_dir: str, season: str) -> str:
    """Save DataFrame to Parquet format with season partitioning.

    Args:
        df: DataFrame to save
        output_dir: Output directory path
        season: Season identifier (e.g., "2024-25")

    Returns:
        Path to the saved file
    """
    path = Path(output_dir) / f"season={season}" / "games.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(
        path,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )
    return str(path)


def load_from_parquet(output_dir: str, season: str) -> pd.DataFrame:
    """Load DataFrame from Parquet format.

    Args:
        output_dir: Output directory path
        season: Season identifier (e.g., "2024-25")

    Returns:
        Loaded DataFrame

    Raises:
        FileNotFoundError: If the parquet file does not exist
    """
    path = Path(output_dir) / f"season={season}" / "games.parquet"

    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found at {path}")

    return pd.read_parquet(path, engine="pyarrow")
