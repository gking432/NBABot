"""
Injury Detection System.
Method 1: Play-by-play absence (3-5 minute detection)
Method 2: Official NBA injury report via nbainjuries package (10-15 min confirmation)
"""
import logging
import json
import os
from typing import Optional, List, Dict, Set
from datetime import datetime

from core.models import InjuryEvent, InjurySeverity, TeamDepth
from data.espn_client import ESPNClient

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Star Player Database
# ─────────────────────────────────────────────

# Top 3 players per team + team depth classification
# Update this monthly — it's a small, stable dataset
DEFAULT_STAR_PLAYERS = {
    "Atlanta Hawks": {"depth": "MULTI_STAR", "stars": ["Trae Young", "Dejounte Murray", "Jalen Johnson"]},
    "Boston Celtics": {"depth": "MULTI_STAR", "stars": ["Jayson Tatum", "Jaylen Brown", "Kristaps Porzingis"]},
    "Brooklyn Nets": {"depth": "SINGLE_STAR", "stars": ["Mikal Bridges", "Cam Thomas", "Dennis Schroder"]},
    "Charlotte Hornets": {"depth": "SINGLE_STAR", "stars": ["LaMelo Ball", "Brandon Miller", "Mark Williams"]},
    "Chicago Bulls": {"depth": "MULTI_STAR", "stars": ["Zach LaVine", "Coby White", "Nikola Vucevic"]},
    "Cleveland Cavaliers": {"depth": "MULTI_STAR", "stars": ["Donovan Mitchell", "Darius Garland", "Evan Mobley"]},
    "Dallas Mavericks": {"depth": "SINGLE_STAR", "stars": ["Luka Doncic", "Kyrie Irving", "PJ Washington"]},
    "Denver Nuggets": {"depth": "SINGLE_STAR", "stars": ["Nikola Jokic", "Jamal Murray", "Michael Porter Jr"]},
    "Detroit Pistons": {"depth": "SINGLE_STAR", "stars": ["Cade Cunningham", "Jaden Ivey", "Ausar Thompson"]},
    "Golden State Warriors": {"depth": "MULTI_STAR", "stars": ["Stephen Curry", "Draymond Green", "Andrew Wiggins"]},
    "Houston Rockets": {"depth": "MULTI_STAR", "stars": ["Jalen Green", "Alperen Sengun", "Fred VanVleet"]},
    "Indiana Pacers": {"depth": "MULTI_STAR", "stars": ["Tyrese Haliburton", "Pascal Siakam", "Myles Turner"]},
    "LA Clippers": {"depth": "MULTI_STAR", "stars": ["James Harden", "Kawhi Leonard", "Norman Powell"]},
    "Los Angeles Lakers": {"depth": "MULTI_STAR", "stars": ["LeBron James", "Anthony Davis", "Austin Reaves"]},
    "Memphis Grizzlies": {"depth": "SINGLE_STAR", "stars": ["Ja Morant", "Desmond Bane", "Jaren Jackson Jr"]},
    "Miami Heat": {"depth": "MULTI_STAR", "stars": ["Jimmy Butler", "Bam Adebayo", "Tyler Herro"]},
    "Milwaukee Bucks": {"depth": "SINGLE_STAR", "stars": ["Giannis Antetokounmpo", "Damian Lillard", "Khris Middleton"]},
    "Minnesota Timberwolves": {"depth": "MULTI_STAR", "stars": ["Anthony Edwards", "Karl-Anthony Towns", "Rudy Gobert"]},
    "New Orleans Pelicans": {"depth": "SINGLE_STAR", "stars": ["Zion Williamson", "Brandon Ingram", "CJ McCollum"]},
    "New York Knicks": {"depth": "MULTI_STAR", "stars": ["Jalen Brunson", "Julius Randle", "OG Anunoby"]},
    "Oklahoma City Thunder": {"depth": "SINGLE_STAR", "stars": ["Shai Gilgeous-Alexander", "Chet Holmgren", "Jalen Williams"]},
    "Orlando Magic": {"depth": "MULTI_STAR", "stars": ["Paolo Banchero", "Franz Wagner", "Jalen Suggs"]},
    "Philadelphia 76ers": {"depth": "MULTI_STAR", "stars": ["Joel Embiid", "Tyrese Maxey", "Paul George"]},
    "Phoenix Suns": {"depth": "MULTI_STAR", "stars": ["Kevin Durant", "Devin Booker", "Bradley Beal"]},
    "Portland Trail Blazers": {"depth": "SINGLE_STAR", "stars": ["Anfernee Simons", "Scoot Henderson", "Jerami Grant"]},
    "Sacramento Kings": {"depth": "MULTI_STAR", "stars": ["De'Aaron Fox", "Domantas Sabonis", "Keegan Murray"]},
    "San Antonio Spurs": {"depth": "SINGLE_STAR", "stars": ["Victor Wembanyama", "Devin Vassell", "Jeremy Sochan"]},
    "Toronto Raptors": {"depth": "SINGLE_STAR", "stars": ["Scottie Barnes", "RJ Barrett", "Immanuel Quickley"]},
    "Utah Jazz": {"depth": "SINGLE_STAR", "stars": ["Lauri Markkanen", "Collin Sexton", "Jordan Clarkson"]},
    "Washington Wizards": {"depth": "SINGLE_STAR", "stars": ["Kyle Kuzma", "Jordan Poole", "Deni Avdija"]},
}


class InjuryDetector:
    """
    Detects potential injuries during live games using two methods:
    1. Play-by-play absence: star player hasn't appeared in events for 5+ min
    2. Official NBA injury report (nbainjuries package): confirmed out
    """

    def __init__(self, espn_client: ESPNClient):
        self.espn = espn_client

        # Load star player data
        self.star_players = self._load_star_players()

        # Track last seen time for each player in each game
        # {game_id: {player_name: last_game_time_seconds}}
        self._last_seen: Dict[str, Dict[str, int]] = {}

        # Active injury flags (to avoid duplicate alerts)
        self._active_flags: Dict[str, Set[str]] = {}  # game_id → set of flagged players

        # Detected events
        self.events: List[InjuryEvent] = []

    def _load_star_players(self) -> dict:
        """Load star player data from file or defaults."""
        data_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data_files", "star_players.json"
        )
        try:
            with open(data_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("Using default star player database")
            return DEFAULT_STAR_PLAYERS

    def get_team_depth(self, team_name: str) -> TeamDepth:
        """Get the depth classification for a team."""
        team_data = self.star_players.get(team_name, {})
        depth = team_data.get("depth", "SINGLE_STAR")
        return TeamDepth(depth)

    def get_star_players(self, team_name: str) -> List[str]:
        """Get the top 3 star players for a team."""
        team_data = self.star_players.get(team_name, {})
        return team_data.get("stars", [])

    def is_star_player(self, team_name: str, player_name: str) -> bool:
        """Check if a player is in the star list for their team."""
        stars = self.get_star_players(team_name)
        # Fuzzy match: check last name
        player_last = player_name.split()[-1].lower() if player_name else ""
        for star in stars:
            star_last = star.split()[-1].lower()
            if star_last == player_last:
                return True
        return False

    # ─────────────────────────────────────────
    # Method 1: Play-by-play absence detection
    # ─────────────────────────────────────────

    def check_pbp_absence(
        self, game_id: str, game_id_nba: str, team_name: str,
        current_game_time_seconds: int
    ) -> List[InjuryEvent]:
        """
        Check if any star players have been absent from play-by-play events
        for an extended period.

        Args:
            game_id: ESPN game ID
            game_id_nba: NBA CDN game ID (for PBP fetch)
            team_name: Canonical team name to check
            current_game_time_seconds: Total seconds elapsed in the game

        Returns:
            List of new InjuryEvent flags (may be empty)
        """
        from core.config import INJURY_ABSENCE_THRESHOLD_SEC

        new_events = []

        if not game_id_nba:
            return new_events

        # Fetch play-by-play
        pbp_actions = self.espn.get_play_by_play(game_id_nba)
        if not pbp_actions:
            return new_events

        # Initialize tracking for this game
        if game_id not in self._last_seen:
            self._last_seen[game_id] = {}
        if game_id not in self._active_flags:
            self._active_flags[game_id] = set()

        # Scan PBP for player mentions
        stars = self.get_star_players(team_name)

        for action in pbp_actions:
            # PBP actions have various formats. Look for player names.
            description = action.get("description", "")
            player_name = action.get("playerNameI", "")  # NBA CDN format

            # Calculate game time of this action
            period = action.get("period", 1)
            clock = action.get("clock", "PT00M00.00S")
            action_game_time = self._pbp_action_to_game_seconds(period, clock)

            # Check if any star player is mentioned
            for star in stars:
                star_last = star.split()[-1].lower()
                if (star_last in description.lower() or
                        star_last in player_name.lower()):
                    self._last_seen[game_id][star] = action_game_time

        # Check for absences
        for star in stars:
            last_seen = self._last_seen[game_id].get(star)

            if last_seen is None:
                # Player hasn't appeared at all — might not be playing tonight
                continue

            absence_seconds = current_game_time_seconds - last_seen

            if (absence_seconds >= INJURY_ABSENCE_THRESHOLD_SEC and
                    star not in self._active_flags[game_id]):
                # Flag this player
                self._active_flags[game_id].add(star)

                event = InjuryEvent(
                    game_id=game_id,
                    player_name=star,
                    team=team_name,
                    detection_method="PBP_ABSENCE",
                    severity=InjurySeverity.POTENTIAL,
                    confirmed=False,
                    action_taken="FLAGGED",
                )
                self.events.append(event)
                new_events.append(event)

                logger.warning(
                    f"INJURY FLAG: {star} ({team_name}) absent from PBP for "
                    f"{absence_seconds}s in game {game_id}"
                )

        return new_events

    def _pbp_action_to_game_seconds(self, period: int, clock: str) -> int:
        """Convert a PBP action's period + clock to total game seconds."""
        # Parse clock (ISO duration: PT12M00.00S)
        try:
            remaining = 720  # Default: 12 minutes
            if clock:
                clock = clock.replace("PT", "").replace("S", "")
                if "M" in clock:
                    parts = clock.split("M")
                    remaining = int(parts[0]) * 60 + int(float(parts[1] or 0))
                else:
                    remaining = int(float(clock))

            completed = max(0, period - 1) * 720
            elapsed_in_period = 720 - remaining
            return completed + elapsed_in_period
        except (ValueError, IndexError):
            return 0

    # ─────────────────────────────────────────
    # Method 2: Official NBA injury report
    # ─────────────────────────────────────────

    def check_official_report(self, team_name: str) -> List[InjuryEvent]:
        """
        Check the official NBA injury report for confirmed injuries.
        Uses the nbainjuries package.

        Returns list of newly confirmed injury events.
        """
        new_events = []

        try:
            from nbainjuries import injury
            from datetime import datetime as dt

            # Get latest injury report
            report_data = injury.get_reportdata(dt.now(), return_df=False)

            if not report_data:
                return new_events

            for entry in report_data:
                player = entry.get("Player Name", "")
                team = entry.get("Team", "")
                status = entry.get("Current Status", "").lower()
                reason = entry.get("Reason", "")

                # Check if this player is on our team and is OUT
                if (self._team_matches(team, team_name) and
                        status == "out" and
                        self.is_star_player(team_name, player)):

                    # Check if we already know about this
                    already_known = any(
                        e.player_name == player and e.confirmed
                        for e in self.events
                    )
                    if not already_known:
                        event = InjuryEvent(
                            game_id="",  # Will be filled by caller
                            player_name=player,
                            team=team_name,
                            detection_method="OFFICIAL_REPORT",
                            severity=InjurySeverity.CONFIRMED,
                            confirmed=True,
                            action_taken="CONFIRMED",
                        )
                        self.events.append(event)
                        new_events.append(event)

                        logger.warning(
                            f"INJURY CONFIRMED: {player} ({team_name}) — {reason}"
                        )

        except ImportError:
            logger.debug("nbainjuries package not installed — skipping official report check")
        except Exception as e:
            logger.warning(f"Error checking official injury report: {e}")

        return new_events

    def _team_matches(self, report_team: str, our_team: str) -> bool:
        """Check if a team name from the injury report matches our canonical name."""
        from data.team_names import normalize_team_name
        return normalize_team_name(report_team) == our_team

    def clear_game(self, game_id: str):
        """Clean up tracking data for a finished game."""
        self._last_seen.pop(game_id, None)
        self._active_flags.pop(game_id, None)
