import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import LiveGameState, GameStatus, Strategy
from data.aggregator import DataAggregator
from strategies.flip import ConservativeHoldFlipStrategy
from trading.position_manager import PositionManager


class StubDB:
    def __init__(self):
        self.logged_trades = []
        self.saved_positions = []

    def get_all_trades_for_replay(self):
        return []

    def get_active_positions_full(self):
        return []

    def has_active_position(self, strategy, game_id):
        return False

    def log_trade(self, trade):
        self.logged_trades.append(trade)

    def save_position(self, position):
        self.saved_positions.append(position)


class StubInjuryDetector:
    pass


class FlipPlumbingTests(unittest.TestCase):
    def test_match_kalshi_market_sets_both_legs(self):
        aggregator = DataAggregator(None, None, None)
        aggregator.kalshi_market_map = {
            "KXNBAGAME-26MAR26BOSNYK-BOS": {
                "event_ticker": "EV1",
                "yes_bid": 58,
                "yes_ask": 60,
                "last_price": 59,
                "status": "open",
            },
            "KXNBAGAME-26MAR26BOSNYK-NYK": {
                "event_ticker": "EV1",
                "yes_bid": 40,
                "yes_ask": 42,
                "last_price": 41,
                "status": "open",
            },
        }
        state = LiveGameState(
            game_id_espn="game1",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            favorite="Boston Celtics",
            underdog="New York Knicks",
        )

        aggregator._match_kalshi_market(state)

        self.assertEqual(state.kalshi_favorite_ticker, "KXNBAGAME-26MAR26BOSNYK-BOS")
        self.assertEqual(state.kalshi_underdog_ticker, "KXNBAGAME-26MAR26BOSNYK-NYK")
        self.assertEqual(state.kalshi_market_ticker, state.kalshi_favorite_ticker)
        self.assertEqual(state.kalshi_yes_ask, 60)
        self.assertEqual(state.kalshi_underdog_ask, 42)

    def test_conservative_hold_flip_builds_underdog_signal(self):
        strategy = ConservativeHoldFlipStrategy({}, bankroll_cents=10000)
        state = LiveGameState(
            game_id_espn="game2",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            favorite="Boston Celtics",
            underdog="New York Knicks",
            quarter=2,
            time_remaining_seconds=500,
            game_status=GameStatus.LIVE,
            opening_spread=5.5,
            deficit_vs_spread=14.0,
            fair_value_home=0.60,
            fair_value_away=0.40,
            kalshi_favorite_ticker="KXNBAGAME-26MAR26BOSNYK-BOS",
            kalshi_underdog_ticker="KXNBAGAME-26MAR26BOSNYK-NYK",
            kalshi_yes_ask=70,
            kalshi_underdog_ask=24,
            kalshi_market_status="open",
            kalshi_underdog_market_status="open",
            kalshi_book_depth=200,
            kalshi_underdog_book_depth=200,
            kalshi_tipoff_price=72,
            kalshi_underdog_tipoff_price=30,
        )

        signal = strategy.check_entry(state)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.team, "New York Knicks")
        self.assertEqual(signal.kalshi_ticker, "KXNBAGAME-26MAR26BOSNYK-NYK")
        self.assertEqual(signal.kalshi_price_cents, 24)
        self.assertEqual(signal.contract_side.value, "UNDERDOG_YES")

    def test_settlement_uses_traded_team(self):
        pm = PositionManager(StubDB(), StubInjuryDetector())
        strategy_positions = pm.get_positions_dict(Strategy.CONSERVATIVE_HOLD_FLIP)
        state = LiveGameState(
            game_id_espn="game3",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            favorite="Boston Celtics",
            underdog="New York Knicks",
            quarter=1,
            time_remaining_seconds=700,
            game_status=GameStatus.LIVE,
            opening_spread=6,
            deficit_vs_spread=13,
            fair_value_home=0.60,
            fair_value_away=0.40,
            kalshi_favorite_ticker="KXNBAGAME-26MAR26BOSNYK-BOS",
            kalshi_underdog_ticker="KXNBAGAME-26MAR26BOSNYK-NYK",
            kalshi_yes_ask=72,
            kalshi_underdog_ask=25,
            kalshi_market_status="open",
            kalshi_underdog_market_status="open",
            kalshi_book_depth=200,
            kalshi_underdog_book_depth=200,
        )
        strategy = ConservativeHoldFlipStrategy(strategy_positions, bankroll_cents=10000)
        signal = strategy.check_entry(state)
        self.assertIsNotNone(signal)
        position = pm.execute_entry(signal, state, fill_price_cents=signal.kalshi_price_cents)

        pm.settle_game("game3", "New York Knicks")

        self.assertEqual(position.team, "New York Knicks")
        self.assertEqual(position.status.value, "CLOSED_SETTLED_WIN")
        self.assertEqual(pm.db.logged_trades[-1].team, "New York Knicks")
        self.assertEqual(pm.db.logged_trades[-1].kalshi_ticker, "KXNBAGAME-26MAR26BOSNYK-NYK")


if __name__ == "__main__":
    unittest.main()
