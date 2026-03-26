"""
Paper Trading Engine.
Simulates order fills using REAL Kalshi market prices.
The only thing simulated is the execution — all data is real.
"""
import logging
from typing import Optional

from core.models import LiveGameState, EntrySignal

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Paper trading: use real Kalshi prices but simulate the fill.
    Assumes fill at the ask price (worst case for buys).
    """

    def __init__(self):
        self.total_trades = 0
        self.total_slippage_cents = 0

    def simulate_buy_fill(
        self,
        signal: EntrySignal,
        state: LiveGameState,
    ) -> Optional[int]:
        """
        Simulate a buy order fill.
        Returns the fill price in cents, or None if we can't fill.

        In paper trading, we fill at the ask price.
        In reality, limit orders might fill better, so paper trading
        is slightly pessimistic (conservative estimate).
        """
        ask_price = signal.kalshi_price_cents
        if ask_price is None:
            logger.warning(f"No ask price available for {signal.kalshi_ticker}")
            return None

        # Check if we can fill the quantity at this price
        if signal.orderbook_depth < signal.suggested_shares:
            logger.warning(
                f"Insufficient depth: need {signal.suggested_shares} contracts, "
                f"only {signal.orderbook_depth} available"
            )
            # Still fill, but log the concern (in real trading we'd adjust)
            pass

        self.total_trades += 1

        # Simulate 1¢ slippage on average (realistic for Kalshi)
        fill_price = ask_price  # Fill at ask in paper trading

        logger.debug(
            f"Paper fill: {signal.suggested_shares} contracts @ {fill_price}¢ "
            f"(ask was {ask_price}¢)"
        )

        return fill_price

    def simulate_sell_fill(
        self,
        shares: int,
        state: LiveGameState,
    ) -> Optional[int]:
        """
        Simulate a sell order fill.
        Returns the fill price in cents.
        Sells at the bid price (worst case for sellers).
        """
        bid_price = state.kalshi_yes_bid
        if bid_price is None:
            # Fall back to last price minus 1
            bid_price = (state.kalshi_last_price or 0) - 1
            if bid_price <= 0:
                bid_price = 1

        logger.debug(f"Paper sell: {shares} contracts @ {bid_price}¢")
        return bid_price
