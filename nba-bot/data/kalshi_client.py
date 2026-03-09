"""
Kalshi API v2 client with RSA key-pair authentication.
Handles market discovery, price fetching, order book depth, and trade history.
"""
import time
import base64
import logging
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from core.config import (
    KALSHI_BASE_URL, KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH
)

logger = logging.getLogger(__name__)


class KalshiClient:
    """Real Kalshi API v2 client with RSA authentication."""

    def __init__(self):
        self.base_url = KALSHI_BASE_URL
        self.api_key_id = KALSHI_API_KEY_ID
        self.private_key = self._load_private_key()
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        # Rate limiting: 10 reads/sec, 5 writes/sec
        self._last_read_time = 0.0
        self._last_write_time = 0.0
        self._read_interval = 0.15   # 150ms between reads (avoids 429s on production)
        self._write_interval = 0.2   # 200ms between writes

        # Cache to avoid redundant calls
        self._market_cache: Dict[str, dict] = {}
        self._cache_ttl = 8  # seconds

    def _load_private_key(self):
        """Load the RSA private key from file."""
        try:
            with open(KALSHI_PRIVATE_KEY_PATH, "rb") as f:
                key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            logger.info("Kalshi RSA private key loaded successfully")
            return key
        except FileNotFoundError:
            logger.error(f"Kalshi private key not found at: {KALSHI_PRIVATE_KEY_PATH}")
            return None
        except Exception as e:
            logger.error(f"Failed to load Kalshi private key: {e}")
            return None

    def _get_auth_headers(self, method: str, path: str) -> dict:
        """Generate authentication headers for a request."""
        if not self.private_key:
            logger.error("No private key loaded — cannot authenticate")
            return {}

        timestamp_ms = str(int(time.time() * 1000))

        # CRITICAL: Strip query params from path before signing
        path_for_signing = path.split("?")[0]
        message = timestamp_ms + method.upper() + path_for_signing

        signature = self.private_key.sign(
            message.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        }

    def _rate_limit_read(self):
        """Enforce read rate limit."""
        now = time.time()
        elapsed = now - self._last_read_time
        if elapsed < self._read_interval:
            time.sleep(self._read_interval - elapsed)
        self._last_read_time = time.time()

    def _rate_limit_write(self):
        """Enforce write rate limit."""
        now = time.time()
        elapsed = now - self._last_write_time
        if elapsed < self._write_interval:
            time.sleep(self._write_interval - elapsed)
        self._last_write_time = time.time()

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make an authenticated GET request with rate limiting and retries."""
        self._rate_limit_read()

        url = f"{self.base_url}{path}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                url += f"?{query}"

        # Auth headers use path relative to base (e.g., /markets/...)
        auth_path = path
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                auth_path += f"?{query}"

        headers = self._get_auth_headers("GET", auth_path)

        for attempt in range(3):
            try:
                resp = self.session.get(url, headers=headers, timeout=10)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait = (attempt + 1) * 2
                    logger.warning(f"Kalshi rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                elif resp.status_code == 401:
                    logger.error("Kalshi auth failed — check API key and private key")
                    return None
                else:
                    logger.warning(f"Kalshi GET {path} returned {resp.status_code}: {resp.text[:200]}")
                    return None

            except requests.exceptions.Timeout:
                logger.warning(f"Kalshi GET {path} timed out (attempt {attempt + 1})")
                time.sleep(1)
            except requests.exceptions.ConnectionError:
                logger.error(f"Kalshi connection error for {path}")
                time.sleep(2)

        logger.error(f"Kalshi GET {path} failed after 3 attempts")
        return None

    def _post(self, path: str, body: dict) -> Optional[dict]:
        """Make an authenticated POST request."""
        self._rate_limit_write()

        url = f"{self.base_url}{path}"
        headers = self._get_auth_headers("POST", path)

        try:
            resp = self.session.post(url, json=body, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                logger.warning(f"Kalshi POST {path} returned {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Kalshi POST {path} error: {e}")
            return None

    # ─────────────────────────────────────────
    # Market Discovery
    # ─────────────────────────────────────────

    def get_nba_events(self) -> List[dict]:
        """Get all open NBA events (games)."""
        result = self._get("/events", params={
            "series_ticker": "KXNBAGAME",
            "status": "open",
            "limit": 50,
        })
        if result and "events" in result:
            return result["events"]
        return []

    def get_markets_for_event(self, event_ticker: str) -> List[dict]:
        """Get all markets within an event."""
        result = self._get("/markets", params={
            "event_ticker": event_ticker,
            "limit": 50,
        })
        if result and "markets" in result:
            return result["markets"]
        return []

    def discover_nba_winner_markets(self) -> Dict[str, dict]:
        """
        Find all currently open NBA winner/moneyline markets.
        Returns: {kalshi_ticker: market_data}
        """
        markets = {}
        events = self.get_nba_events()

        for event in events:
            event_ticker = event.get("event_ticker", "")
            event_markets = self.get_markets_for_event(event_ticker)

            for market in event_markets:
                # Look for winner/moneyline markets
                # Kalshi uses various subtitle formats — check for "winner" type
                ticker = market.get("ticker", "")
                subtitle = market.get("subtitle", "").lower()
                title = market.get("title", "").lower()

                if any(kw in title + subtitle for kw in ["win", "winner", "victory"]):
                    markets[ticker] = {
                        "ticker": ticker,
                        "event_ticker": event_ticker,
                        "title": market.get("title", ""),
                        "subtitle": market.get("subtitle", ""),
                        "yes_bid": market.get("yes_bid"),
                        "yes_ask": market.get("yes_ask"),
                        "no_bid": market.get("no_bid"),
                        "no_ask": market.get("no_ask"),
                        "last_price": market.get("last_price"),
                        "volume_24h": market.get("volume_24h", 0),
                        "open_interest": market.get("open_interest", 0),
                        "status": market.get("status", ""),
                    }

        logger.info(f"Discovered {len(markets)} NBA winner markets on Kalshi")
        return markets

    # ─────────────────────────────────────────
    # Market Data
    # ─────────────────────────────────────────

    def get_market(self, ticker: str) -> Optional[dict]:
        """Get current market data for a specific ticker."""
        result = self._get(f"/markets/{ticker}")
        if result and "market" in result:
            return result["market"]
        return None

    def get_market_prices(self, ticker: str) -> Optional[dict]:
        """Get just the price data we need. Returns dict with yes_bid, yes_ask, etc."""
        market = self.get_market(ticker)
        if not market:
            return None

        return {
            "yes_bid": market.get("yes_bid"),     # cents
            "yes_ask": market.get("yes_ask"),     # cents
            "no_bid": market.get("no_bid"),
            "no_ask": market.get("no_ask"),
            "last_price": market.get("last_price"),
            "volume": market.get("volume_24h", 0),
            "open_interest": market.get("open_interest", 0),
            "status": market.get("status", ""),
        }

    def get_orderbook(self, ticker: str) -> Optional[dict]:
        """
        Get order book depth.
        Returns: {yes: [[price, qty], ...], no: [[price, qty], ...]}
        """
        result = self._get(f"/markets/{ticker}/orderbook")
        if result and "orderbook" in result:
            return result["orderbook"]
        return None

    def get_orderbook_depth_at_ask(self, ticker: str, levels: int = 5) -> int:
        """
        Get total quantity available in the top N ask levels.
        This tells us how many contracts we can actually buy near the current price.
        """
        book = self.get_orderbook(ticker)
        if not book:
            return 0

        yes_levels = book.get("yes") or []
        if not isinstance(yes_levels, list):
            return 0

        total_depth = 0
        for i, level in enumerate(yes_levels[:levels]):
            if isinstance(level, list) and len(level) >= 2:
                total_depth += level[1]
            elif isinstance(level, dict):
                total_depth += level.get("quantity", 0)

        return total_depth

    # ─────────────────────────────────────────
    # Trade History (for opening/tipoff price)
    # ─────────────────────────────────────────

    def get_trade_history(self, ticker: str, limit: int = 100) -> List[dict]:
        """
        Get recent trades for a market.
        Returns list of: {yes_price, no_price, count, created_time, taker_side}
        """
        result = self._get(f"/markets/trades", params={
            "ticker": ticker,
            "limit": limit,
        })
        if result and "trades" in result:
            return result["trades"]
        return []

    def get_opening_price(self, ticker: str) -> Optional[int]:
        """Get the first trade price (market opening price) in cents."""
        trades = self.get_trade_history(ticker, limit=100)
        if not trades:
            return None

        # Trades are typically returned newest-first
        # We want the oldest trade = the opening price
        oldest = trades[-1] if trades else None
        if oldest:
            return oldest.get("yes_price")
        return None

    # ─────────────────────────────────────────
    # Order Placement (for live trading)
    # ─────────────────────────────────────────

    def place_order(
        self,
        ticker: str,
        side: str,        # "yes" or "no"
        action: str,      # "buy" or "sell"
        count: int,       # number of contracts
        price_cents: int,  # limit price in cents
    ) -> Optional[dict]:
        """
        Place a limit order on Kalshi.
        ONLY used in live trading mode (Week 4+).
        """
        body = {
            "ticker": ticker,
            "action": action,
            "side": side,
            "count": count,
            "type": "limit",
        }

        # Price field name depends on side
        if side == "yes":
            body["yes_price"] = price_cents
        else:
            body["no_price"] = price_cents

        result = self._post("/portfolio/orders", body)
        if result:
            logger.info(f"Order placed: {action} {count}x {side} @ {price_cents}¢ on {ticker}")
        return result

    def get_balance(self) -> Optional[int]:
        """Get account balance in cents."""
        result = self._get("/portfolio/balance")
        if result:
            return result.get("balance")
        return None

    def get_positions(self) -> List[dict]:
        """Get all current positions."""
        result = self._get("/portfolio/positions")
        if result and "market_positions" in result:
            return result["market_positions"]
        return []

    # ─────────────────────────────────────────
    # Health Check
    # ─────────────────────────────────────────

    def health_check(self) -> bool:
        """Verify we can connect and authenticate."""
        try:
            result = self._get("/exchange/status")
            if result:
                logger.info(f"Kalshi connection OK. Exchange status: {result}")
                return True
        except Exception as e:
            logger.error(f"Kalshi health check failed: {e}")
        return False
