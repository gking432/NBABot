"""
ESPN scoreboard client for live NBA scores.
Falls back to NBA CDN if ESPN is down.
"""
import logging
import requests
from typing import Optional, List, Dict
from datetime import datetime

from core.config import ESPN_BASE_URL, NBA_CDN_BASE_URL
from core.models import GameStatus
from data.team_names import normalize_team_name

logger = logging.getLogger(__name__)


class ESPNClient:
    """Fetches live NBA scores from ESPN's free API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; NBABot/1.0)"
        })
        self._espn_available = True

    def get_live_games(self) -> List[dict]:
        """
        Get all today's games with scores, quarter, time, spread.
        Returns normalized game dicts.

        Each dict contains:
            game_id_espn, home_team, away_team, home_score, away_score,
            quarter, time_remaining_seconds, game_status, opening_spread,
            favorite, underdog
        """
        games = self._fetch_espn()
        if games is None:
            logger.warning("ESPN unavailable, falling back to NBA CDN")
            games = self._fetch_nba_cdn()

        return games or []

    # ─────────────────────────────────────────
    # ESPN Fetch
    # ─────────────────────────────────────────

    def _fetch_espn(self) -> Optional[List[dict]]:
        """Fetch from ESPN scoreboard API."""
        try:
            url = f"{ESPN_BASE_URL}/scoreboard"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"ESPN returned status {resp.status_code}")
                self._espn_available = False
                return None

            data = resp.json()
            self._espn_available = True
            games = []

            for event in data.get("events", []):
                game = self._parse_espn_event(event)
                if game:
                    games.append(game)

            return games

        except requests.exceptions.RequestException as e:
            logger.warning(f"ESPN request failed: {e}")
            self._espn_available = False
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"ESPN parse error: {e}")
            return None

    def _parse_espn_event(self, event: dict) -> Optional[dict]:
        """Parse a single ESPN event into our format."""
        try:
            game_id = event.get("id", "")
            competition = event["competitions"][0]
            status_data = event.get("status", {})

            # Parse game status
            state = status_data.get("type", {}).get("state", "pre")
            period = status_data.get("period", 0)
            clock = status_data.get("displayClock", "0:00")

            if state == "pre":
                game_status = GameStatus.PRE
            elif state == "post":
                game_status = GameStatus.FINAL
            elif period == 2 and clock == "0:00":
                # Check for halftime
                game_status = GameStatus.HALFTIME
            else:
                game_status = GameStatus.LIVE

            # Parse time remaining
            time_remaining_seconds = self._parse_clock(clock)

            # Parse teams and scores
            competitors = competition.get("competitors", [])
            home_team = ""
            away_team = ""
            home_score = 0
            away_score = 0

            for comp in competitors:
                team_name = normalize_team_name(
                    comp.get("team", {}).get("displayName", "")
                )
                score = int(comp.get("score", "0") or "0")

                if comp.get("homeAway") == "home":
                    home_team = team_name
                    home_score = score
                else:
                    away_team = team_name
                    away_score = score

            # Parse spread (PRE-GAME ONLY — stale during live play)
            opening_spread = 0.0
            favorite = home_team
            underdog = away_team

            odds_data = competition.get("odds", [])
            if odds_data:
                spread = odds_data[0].get("spread")
                if spread is not None:
                    opening_spread = float(spread)
                    # Negative spread = home team is favored
                    if opening_spread < 0:
                        favorite = home_team
                        underdog = away_team
                    else:
                        favorite = away_team
                        underdog = home_team

            return {
                "game_id_espn": game_id,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "quarter": period,
                "time_remaining_seconds": time_remaining_seconds,
                "game_status": game_status,
                "opening_spread": abs(opening_spread),  # Store as positive
                "favorite": favorite,
                "underdog": underdog,
            }

        except (KeyError, IndexError, ValueError) as e:
            logger.warning(f"Failed to parse ESPN event: {e}")
            return None

    def _parse_clock(self, clock_str: str) -> int:
        """Parse 'MM:SS' or 'M:SS' to seconds."""
        try:
            if not clock_str or clock_str == "0:00":
                return 0
            parts = clock_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            return 0
        except (ValueError, IndexError):
            return 0

    # ─────────────────────────────────────────
    # NBA CDN Fallback
    # ─────────────────────────────────────────

    def _fetch_nba_cdn(self) -> Optional[List[dict]]:
        """Fetch from NBA CDN as fallback."""
        try:
            url = f"{NBA_CDN_BASE_URL}/scoreboard/todaysScoreboard_00.json"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                logger.error(f"NBA CDN returned status {resp.status_code}")
                return None

            data = resp.json()
            games = []

            scoreboard = data.get("scoreboard", {})
            for game_data in scoreboard.get("games", []):
                game = self._parse_nba_cdn_game(game_data)
                if game:
                    games.append(game)

            return games

        except Exception as e:
            logger.error(f"NBA CDN fetch failed: {e}")
            return None

    def _parse_nba_cdn_game(self, game_data: dict) -> Optional[dict]:
        """Parse a single NBA CDN game into our format."""
        try:
            game_id = game_data.get("gameId", "")
            status = game_data.get("gameStatus", 1)  # 1=pre, 2=live, 3=final

            if status == 1:
                game_status = GameStatus.PRE
            elif status == 3:
                game_status = GameStatus.FINAL
            else:
                game_status = GameStatus.LIVE

            period = game_data.get("period", 0)
            clock = game_data.get("gameClock", "PT00M00.00S")

            # Parse ISO duration (PT12M00.00S)
            time_remaining_seconds = self._parse_nba_clock(clock)

            home = game_data.get("homeTeam", {})
            away = game_data.get("awayTeam", {})

            home_team = normalize_team_name(
                home.get("teamCity", "") + " " + home.get("teamName", "")
            )
            away_team = normalize_team_name(
                away.get("teamCity", "") + " " + away.get("teamName", "")
            )

            return {
                "game_id_espn": "",  # No ESPN ID from CDN
                "game_id_nba": game_id,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home.get("score", 0),
                "away_score": away.get("score", 0),
                "quarter": period,
                "time_remaining_seconds": time_remaining_seconds,
                "game_status": game_status,
                "opening_spread": 0.0,  # Not available from CDN
                "favorite": home_team,  # Unknown without spread
                "underdog": away_team,
            }

        except Exception as e:
            logger.warning(f"Failed to parse NBA CDN game: {e}")
            return None

    def _parse_nba_clock(self, clock: str) -> int:
        """Parse NBA CDN clock format 'PT12M00.00S' to seconds."""
        try:
            if not clock or clock == "PT00M00.00S":
                return 0
            # Remove PT prefix and S suffix
            clock = clock.replace("PT", "").replace("S", "")
            if "M" in clock:
                parts = clock.split("M")
                minutes = int(parts[0])
                seconds = float(parts[1]) if parts[1] else 0
                return int(minutes * 60 + seconds)
            return int(float(clock))
        except (ValueError, IndexError):
            return 0

    # ─────────────────────────────────────────
    # Play-by-play (for injury detection + momentum)
    # ─────────────────────────────────────────

    def get_play_by_play(self, game_id_nba: str) -> Optional[List[dict]]:
        """
        Get play-by-play data from NBA CDN.
        Used for injury absence detection and momentum scoring.
        """
        if not game_id_nba:
            return None

        try:
            url = f"{NBA_CDN_BASE_URL}/playbyplay/playbyplay_{game_id_nba}.json"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            game = data.get("game", {})
            actions = game.get("actions", [])
            return actions

        except Exception as e:
            logger.warning(f"PBP fetch failed for {game_id_nba}: {e}")
            return None

    def get_box_score(self, game_id_nba: str) -> Optional[dict]:
        """Get box score for a specific game (player minutes, etc.)."""
        if not game_id_nba:
            return None

        try:
            url = f"{NBA_CDN_BASE_URL}/boxscore/boxscore_{game_id_nba}.json"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception as e:
            logger.warning(f"Box score fetch failed for {game_id_nba}: {e}")
            return None
