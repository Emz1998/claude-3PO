"""Fetch and normalize NBA team statistics."""

import pandas as pd

from pipeline.data.nba_client import NBAStatsClient


def fetch_team_stats(season: str = "2024-25") -> pd.DataFrame:
    """Fetch and normalize team game statistics for a season.

    Args:
        season: NBA season in format "YYYY-YY" (default: "2024-25")

    Returns:
        Normalized DataFrame with team game logs
    """
    client = NBAStatsClient(season=season)
    df = client.fetch_league_game_log(season=season)

    # Normalize: lowercase columns
    df.columns = df.columns.str.lower()

    # Parse game_date to datetime
    df["game_date"] = pd.to_datetime(df["game_date"])

    # Add season column
    df["season"] = season

    return df.copy()
