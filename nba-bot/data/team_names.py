"""
Team name normalization.
ESPN, NBA CDN, The Odds API, and Kalshi all use different names.
This maps everything to a single canonical name.
"""

# Canonical name → list of known aliases across all APIs
TEAM_ALIASES = {
    "Atlanta Hawks": ["Atlanta Hawks", "Hawks", "ATL", "atlanta hawks", "Atlanta"],
    "Boston Celtics": ["Boston Celtics", "Celtics", "BOS", "boston celtics", "Boston"],
    "Brooklyn Nets": ["Brooklyn Nets", "Nets", "BKN", "BRK", "brooklyn nets", "Brooklyn"],
    "Charlotte Hornets": ["Charlotte Hornets", "Hornets", "CHA", "charlotte hornets", "Charlotte"],
    "Chicago Bulls": ["Chicago Bulls", "Bulls", "CHI", "chicago bulls", "Chicago"],
    "Cleveland Cavaliers": ["Cleveland Cavaliers", "Cavaliers", "Cavs", "CLE", "cleveland cavaliers", "Cleveland"],
    "Dallas Mavericks": ["Dallas Mavericks", "Mavericks", "Mavs", "DAL", "dallas mavericks", "Dallas"],
    "Denver Nuggets": ["Denver Nuggets", "Nuggets", "DEN", "denver nuggets", "Denver"],
    "Detroit Pistons": ["Detroit Pistons", "Pistons", "DET", "detroit pistons", "Detroit"],
    "Golden State Warriors": ["Golden State Warriors", "Warriors", "GS", "GSW", "golden state warriors", "Golden State"],
    "Houston Rockets": ["Houston Rockets", "Rockets", "HOU", "houston rockets", "Houston"],
    "Indiana Pacers": ["Indiana Pacers", "Pacers", "IND", "indiana pacers", "Indiana"],
    "LA Clippers": ["LA Clippers", "Los Angeles Clippers", "Clippers", "LAC", "la clippers", "L.A. Clippers"],
    "Los Angeles Lakers": ["Los Angeles Lakers", "Lakers", "LAL", "LA Lakers", "los angeles lakers", "L.A. Lakers"],
    "Memphis Grizzlies": ["Memphis Grizzlies", "Grizzlies", "MEM", "memphis grizzlies", "Memphis"],
    "Miami Heat": ["Miami Heat", "Heat", "MIA", "miami heat", "Miami"],
    "Milwaukee Bucks": ["Milwaukee Bucks", "Bucks", "MIL", "milwaukee bucks", "Milwaukee"],
    "Minnesota Timberwolves": ["Minnesota Timberwolves", "Timberwolves", "Wolves", "MIN", "minnesota timberwolves", "Minnesota"],
    "New Orleans Pelicans": ["New Orleans Pelicans", "Pelicans", "NOP", "NO", "new orleans pelicans", "New Orleans"],
    "New York Knicks": ["New York Knicks", "Knicks", "NYK", "NY", "new york knicks", "New York"],
    "Oklahoma City Thunder": ["Oklahoma City Thunder", "Thunder", "OKC", "oklahoma city thunder", "Oklahoma City"],
    "Orlando Magic": ["Orlando Magic", "Magic", "ORL", "orlando magic", "Orlando"],
    "Philadelphia 76ers": ["Philadelphia 76ers", "76ers", "Sixers", "PHI", "philadelphia 76ers", "Philadelphia"],
    "Phoenix Suns": ["Phoenix Suns", "Suns", "PHX", "PHO", "phoenix suns", "Phoenix"],
    "Portland Trail Blazers": ["Portland Trail Blazers", "Trail Blazers", "Blazers", "POR", "portland trail blazers", "Portland"],
    "Sacramento Kings": ["Sacramento Kings", "Kings", "SAC", "sacramento kings", "Sacramento"],
    "San Antonio Spurs": ["San Antonio Spurs", "Spurs", "SAS", "SA", "san antonio spurs", "San Antonio"],
    "Toronto Raptors": ["Toronto Raptors", "Raptors", "TOR", "toronto raptors", "Toronto"],
    "Utah Jazz": ["Utah Jazz", "Jazz", "UTA", "utah jazz", "Utah"],
    "Washington Wizards": ["Washington Wizards", "Wizards", "WAS", "WSH", "washington wizards", "Washington"],
}

# Build reverse lookup: any alias → canonical name
_ALIAS_TO_CANONICAL = {}
for canonical, aliases in TEAM_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower().strip()] = canonical


def normalize_team_name(name: str) -> str:
    """
    Convert any team name variant to canonical form.
    Returns the canonical name or the original if no match found.
    """
    if not name:
        return name
    
    lookup = name.lower().strip()
    
    # Direct lookup
    if lookup in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[lookup]
    
    # Try partial match (e.g., "L.A. Lakers" might not be in aliases)
    for alias_lower, canonical in _ALIAS_TO_CANONICAL.items():
        if alias_lower in lookup or lookup in alias_lower:
            return canonical
    
    # No match found — log a warning and return as-is
    import logging
    logging.warning(f"Could not normalize team name: '{name}'")
    return name


def get_abbreviation(canonical_name: str) -> str:
    """Get the standard 3-letter abbreviation for a team."""
    abbrevs = {
        "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
        "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
        "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
        "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
        "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
        "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
        "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
        "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
        "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
        "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
        "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
        "Utah Jazz": "UTA", "Washington Wizards": "WAS",
    }
    return abbrevs.get(canonical_name, "???")


def teams_match(name1: str, name2: str) -> bool:
    """Check if two team names refer to the same team."""
    return normalize_team_name(name1) == normalize_team_name(name2)
