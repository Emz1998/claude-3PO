"""NBA Stats API client with rate limiting and retry logic."""

import logging
import random
import time

import pandas as pd
import requests
from nba_api.stats.endpoints import LeagueGameLog
from nba_api.stats.library.http import STATS_HEADERS as DEFAULT_HEADERS
from nba_api.stats.static import teams

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


class NBAStatsClient:
    """Client for fetching NBA statistics with rate limiting and retry logic."""

    def __init__(self, season: str, rate_limit_delay: float = 1.0) -> None:
        """Initialize the NBA Stats client.

        Args:
            season: NBA season in format "YYYY-YY" (e.g., "2024-25")
            rate_limit_delay: Delay in seconds between API calls
        """
        self.season = season
        self.rate_limit_delay = rate_limit_delay
        self._headers = dict(DEFAULT_HEADERS)
        self._logger = logging.getLogger(__name__)

    def fetch_league_game_log(self, season: str) -> pd.DataFrame:
        """Fetch game log for all teams in a season.

        Args:
            season: NBA season in format "YYYY-YY" (e.g., "2024-25")

        Returns:
            DataFrame with game logs for all teams

        Raises:
            ValueError: If the API returns an empty DataFrame
            RuntimeError: If all retries are exhausted
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                endpoint = LeagueGameLog(
                    season=season,
                    player_or_team_abbreviation="T",
                    headers=self._headers,
                    timeout=60,
                )
                df = endpoint.league_game_log.get_data_frame()

                if df.empty:
                    raise ValueError(
                        f"LeagueGameLog returned empty DataFrame for season {season}"
                    )

                time.sleep(self.rate_limit_delay)
                return df

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < MAX_RETRIES:
                    backoff = RETRY_BASE_DELAY ** (attempt - 1)
                    jitter = random.uniform(0, 1)
                    sleep_time = backoff + jitter
                    self._logger.warning(
                        f"Attempt {attempt}/{MAX_RETRIES} failed: {e}. "
                        f"Retrying in {sleep_time:.2f}s"
                    )
                    time.sleep(sleep_time)
                else:
                    raise RuntimeError(
                        f"Failed to fetch LeagueGameLog after {MAX_RETRIES} attempts"
                    ) from e

        raise RuntimeError(
            f"Failed to fetch LeagueGameLog after {MAX_RETRIES} attempts"
        )

    def get_all_team_ids(self) -> list[int]:
        """Get all NBA team IDs.

        Returns:
            List of 30 team IDs
        """
        return [t["id"] for t in teams.get_teams()]
