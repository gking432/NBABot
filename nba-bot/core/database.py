"""
Database layer. SQLite with SQLAlchemy.
Logs every game snapshot, signal, trade, injury event, and daily performance.
This is the gold mine for analysis and dashboard data.
"""
import logging
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean,
    DateTime, Text, Index, text,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from core.config import DB_PATH
from core.models import (
    LiveGameState, EntrySignal, TradeRecord, Position,
    InjuryEvent, DailyPerformance, Strategy, TradeAction, GameMode,
    BOUNCEBACK_STRATEGY_DB_ALIASES,
    strategy_from_stored_value,
)

logger = logging.getLogger(__name__)

Base = declarative_base()

# Bounceback row match: current enum value plus any legacy labels still in SQLite.
_BOUNCEBACK_DB_VALUES = (Strategy.GARBAGE_TIME.value,) + BOUNCEBACK_STRATEGY_DB_ALIASES


# ─────────────────────────────────────────────
# Table Definitions
# ─────────────────────────────────────────────

class GameSnapshotRow(Base):
    """Logged every 30 seconds per live game."""
    __tablename__ = "game_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    game_id = Column(String, index=True)
    kalshi_ticker = Column(String)
    home_team = Column(String)
    away_team = Column(String)
    home_score = Column(Integer)
    away_score = Column(Integer)
    quarter = Column(Integer)
    time_remaining = Column(Integer)
    game_status = Column(String)
    opening_spread = Column(Float)
    current_spread = Column(Float, nullable=True)
    fair_value_home = Column(Float, nullable=True)
    fair_value_away = Column(Float, nullable=True)
    kalshi_yes_bid = Column(Integer, nullable=True)
    kalshi_yes_ask = Column(Integer, nullable=True)
    kalshi_last_price = Column(Integer, nullable=True)
    kalshi_volume = Column(Integer, default=0)
    kalshi_book_depth = Column(Integer, default=0)
    deficit_vs_spread = Column(Float, default=0)
    edge = Column(Float, nullable=True)
    price_drop_pct = Column(Float, default=0)
    momentum_score = Column(Float, default=0)


class SignalRow(Base):
    """Every signal generated, whether traded or not."""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    game_id = Column(String, index=True)
    team = Column(String)
    strategy = Column(String, index=True)
    signal_type = Column(String)  # "ENTRY_1", "ENTRY_2", "EXIT_TP1", etc.
    entry_number = Column(Integer, nullable=True)
    deficit = Column(Float)
    edge = Column(Float, nullable=True)
    price_drop_pct = Column(Float, nullable=True)
    kalshi_price = Column(Integer)
    pre_game_spread = Column(Float, default=0)
    confidence = Column(Integer, default=50)
    reason = Column(Text)
    action_taken = Column(Boolean, default=False)
    skip_reason = Column(Text, nullable=True)


class TradeRow(Base):
    """Immutable trade log."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    position_id = Column(String, index=True)
    game_id = Column(String, index=True)
    kalshi_ticker = Column(String)
    team = Column(String)
    strategy = Column(String, index=True)
    action = Column(String)  # BUY, SELL_PARTIAL, SELL_ALL, SETTLED_WIN, SETTLED_LOSS
    entry_number = Column(Integer, nullable=True)
    price_cents = Column(Integer)
    shares = Column(Integer)
    total_cents = Column(Integer)
    pnl_cents = Column(Integer, nullable=True)
    reason = Column(Text)
    game_quarter = Column(Integer)
    game_time_remaining = Column(Integer)
    game_score_home = Column(Integer)
    game_score_away = Column(Integer)
    deficit_vs_spread = Column(Float)
    fair_value = Column(Float, nullable=True)
    edge = Column(Float, nullable=True)
    price_drop_pct = Column(Float, nullable=True)
    orderbook_depth = Column(Integer, default=0)
    game_mode = Column(String, default="OFFENSIVE")


class PositionRow(Base):
    """Position state (active and historical)."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(String, unique=True, index=True)
    game_id = Column(String, index=True)
    kalshi_ticker = Column(String)
    team = Column(String)
    strategy = Column(String, index=True)
    total_shares = Column(Integer, default=0)
    total_cost_cents = Column(Integer, default=0)
    avg_cost_cents = Column(Float, default=0)
    entry_count = Column(Integer, default=0)
    game_budget_used = Column(Integer, default=0)
    nuclear_budget_used = Column(Integer, default=0)
    shares_remaining = Column(Integer, default=0)
    status = Column(String, default="ACTIVE")
    capital_recovered = Column(Boolean, default=False)
    capital_recovered_amount = Column(Integer, default=0)
    highest_price_cents = Column(Integer, default=0)
    current_mode = Column(String, default="OFFENSIVE")
    realized_pnl_cents = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class InjuryEventRow(Base):
    """Tracked injury events."""
    __tablename__ = "injury_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    game_id = Column(String)
    player_name = Column(String)
    team = Column(String)
    detection_method = Column(String)
    severity = Column(String)
    confirmed = Column(Boolean, default=False)
    action_taken = Column(Text)
    position_id = Column(String, nullable=True)


class DailyPerformanceRow(Base):
    """End-of-day summary per strategy."""
    __tablename__ = "daily_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, index=True)
    strategy = Column(String, index=True)
    starting_balance_cents = Column(Integer)
    ending_balance_cents = Column(Integer)
    pnl_cents = Column(Integer)
    trades_count = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    best_trade_cents = Column(Integer, default=0)
    worst_trade_cents = Column(Integer, default=0)
    avg_win_cents = Column(Integer, default=0)
    avg_loss_cents = Column(Integer, default=0)


# ─────────────────────────────────────────────
# Database Manager
# ─────────────────────────────────────────────

class Database:
    """Handles all database operations."""

    def __init__(self):
        # Ensure the db directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate_legacy_strategy_names()
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Database initialized at {DB_PATH}")

    def _migrate_legacy_strategy_names(self):
        """Rename legacy Heavy Favorite labels to GARBAGE_TIME (Bounceback)."""
        try:
            with self.engine.begin() as conn:
                for table in ("trades", "positions", "signals", "daily_performance"):
                    for old in BOUNCEBACK_STRATEGY_DB_ALIASES:
                        r = conn.execute(
                            text(
                                f"UPDATE {table} SET strategy = :new "
                                "WHERE strategy = :old"
                            ),
                            {"new": "GARBAGE_TIME", "old": old},
                        )
                        n = r.rowcount or 0
                        if n:
                            logger.info(
                                "Migrated %s rows in %s: %r → GARBAGE_TIME",
                                n,
                                table,
                                old,
                            )
        except Exception as e:
            logger.warning("Legacy strategy migration skipped: %s", e)

    def get_session(self) -> Session:
        return self.SessionLocal()

    # ─────────────────────────────────────────
    # Game Snapshots
    # ─────────────────────────────────────────

    def log_game_snapshot(self, state: LiveGameState):
        """Log a game state snapshot. Call every 30 seconds per live game."""
        session = self.get_session()
        try:
            row = GameSnapshotRow(
                game_id=state.game_id_espn,
                kalshi_ticker=state.kalshi_market_ticker or "",
                home_team=state.home_team,
                away_team=state.away_team,
                home_score=state.home_score,
                away_score=state.away_score,
                quarter=state.quarter,
                time_remaining=state.time_remaining_seconds,
                game_status=state.game_status.value,
                opening_spread=state.opening_spread,
                current_spread=state.current_spread,
                fair_value_home=state.fair_value_home,
                fair_value_away=state.fair_value_away,
                kalshi_yes_bid=state.kalshi_yes_bid,
                kalshi_yes_ask=state.kalshi_yes_ask,
                kalshi_last_price=state.kalshi_last_price,
                kalshi_volume=state.kalshi_volume,
                kalshi_book_depth=state.kalshi_book_depth,
                deficit_vs_spread=state.deficit_vs_spread,
                edge=state.edge_conservative,
                price_drop_pct=state.price_drop_from_tipoff,
                momentum_score=state.momentum_score,
            )
            session.add(row)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log game snapshot: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────
    # Signals
    # ─────────────────────────────────────────

    def log_signal(self, signal: EntrySignal):
        """Log an entry signal (whether acted on or not)."""
        session = self.get_session()
        try:
            row = SignalRow(
                signal_id=signal.signal_id,
                game_id=signal.game_id,
                team=signal.team,
                strategy=signal.strategy.value,
                signal_type=f"ENTRY_{signal.entry_number}",
                entry_number=signal.entry_number,
                deficit=signal.deficit_vs_spread,
                edge=signal.edge,
                price_drop_pct=signal.price_drop_pct,
                kalshi_price=signal.kalshi_price_cents,
                pre_game_spread=signal.pre_game_spread,
                confidence=signal.confidence,
                reason=signal.reason,
                action_taken=signal.action_taken,
                skip_reason=signal.skip_reason,
            )
            session.add(row)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log signal: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────
    # Trades
    # ─────────────────────────────────────────

    def log_trade(self, trade: TradeRecord):
        """Log an executed trade."""
        session = self.get_session()
        try:
            row = TradeRow(
                trade_id=trade.trade_id,
                position_id=trade.position_id,
                game_id=trade.game_id,
                kalshi_ticker=trade.kalshi_ticker,
                team=trade.team,
                strategy=trade.strategy.value,
                action=trade.action.value,
                entry_number=trade.entry_number,
                price_cents=trade.price_cents,
                shares=trade.shares,
                total_cents=trade.total_cents,
                pnl_cents=trade.pnl_cents,
                reason=trade.reason,
                game_quarter=trade.game_quarter,
                game_time_remaining=trade.game_time_remaining_seconds,
                game_score_home=trade.game_score_home,
                game_score_away=trade.game_score_away,
                deficit_vs_spread=trade.deficit_vs_spread,
                fair_value=trade.fair_value,
                edge=trade.edge,
                price_drop_pct=trade.price_drop_pct,
                orderbook_depth=trade.orderbook_depth,
                game_mode=trade.game_mode.value,
            )
            session.add(row)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log trade: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────
    # Positions
    # ─────────────────────────────────────────

    def save_position(self, pos: Position):
        """Insert or update a position."""
        session = self.get_session()
        try:
            existing = session.query(PositionRow).filter_by(
                position_id=pos.position_id
            ).first()

            if existing:
                existing.total_shares = pos.total_shares
                existing.total_cost_cents = pos.total_cost_cents
                existing.avg_cost_cents = pos.avg_cost_cents
                existing.entry_count = pos.entry_count
                existing.game_budget_used = pos.game_budget_used_cents
                existing.nuclear_budget_used = pos.nuclear_budget_used_cents
                existing.shares_remaining = pos.shares_remaining
                existing.status = pos.status.value
                existing.capital_recovered = pos.capital_recovered
                existing.capital_recovered_amount = pos.capital_recovered_amount_cents
                existing.highest_price_cents = pos.highest_price_cents
                existing.current_mode = pos.current_mode.value
                existing.realized_pnl_cents = pos.realized_pnl_cents
                existing.updated_at = datetime.utcnow()
                existing.closed_at = pos.closed_at
            else:
                row = PositionRow(
                    position_id=pos.position_id,
                    game_id=pos.game_id,
                    kalshi_ticker=pos.kalshi_ticker,
                    team=pos.team,
                    strategy=pos.strategy.value,
                    total_shares=pos.total_shares,
                    total_cost_cents=pos.total_cost_cents,
                    avg_cost_cents=pos.avg_cost_cents,
                    entry_count=pos.entry_count,
                    game_budget_used=pos.game_budget_used_cents,
                    nuclear_budget_used=pos.nuclear_budget_used_cents,
                    shares_remaining=pos.shares_remaining,
                    status=pos.status.value,
                    capital_recovered=pos.capital_recovered,
                    capital_recovered_amount=pos.capital_recovered_amount_cents,
                    highest_price_cents=pos.highest_price_cents,
                    current_mode=pos.current_mode.value,
                    realized_pnl_cents=pos.realized_pnl_cents,
                )
                session.add(row)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save position: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────
    # Injury Events
    # ─────────────────────────────────────────

    def log_injury_event(self, event: InjuryEvent):
        """Log a detected injury event."""
        session = self.get_session()
        try:
            row = InjuryEventRow(
                event_id=event.event_id,
                game_id=event.game_id,
                player_name=event.player_name,
                team=event.team,
                detection_method=event.detection_method,
                severity=event.severity.value,
                confirmed=event.confirmed,
                action_taken=event.action_taken,
                position_id=event.position_id,
            )
            session.add(row)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log injury event: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────
    # Daily Performance
    # ─────────────────────────────────────────

    def log_daily_performance(self, perf: DailyPerformance):
        """Log end-of-day performance summary."""
        session = self.get_session()
        try:
            row = DailyPerformanceRow(
                date=perf.date,
                strategy=perf.strategy.value,
                starting_balance_cents=perf.starting_balance_cents,
                ending_balance_cents=perf.ending_balance_cents,
                pnl_cents=perf.pnl_cents,
                trades_count=perf.trades_count,
                wins=perf.wins,
                losses=perf.losses,
                best_trade_cents=perf.best_trade_cents,
                worst_trade_cents=perf.worst_trade_cents,
                avg_win_cents=perf.avg_win_cents,
                avg_loss_cents=perf.avg_loss_cents,
            )
            session.add(row)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log daily performance: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────
    # Query Methods (for dashboard)
    # ─────────────────────────────────────────

    def get_trades(self, strategy: Optional[str] = None,
                   since: Optional[datetime] = None,
                   limit: int = 100) -> List[dict]:
        """Get trades, optionally filtered by strategy and date."""
        session = self.get_session()
        try:
            query = session.query(TradeRow)
            if strategy:
                if strategy == "GARBAGE_TIME":
                    query = query.filter(TradeRow.strategy.in_(_BOUNCEBACK_DB_VALUES))
                else:
                    query = query.filter(TradeRow.strategy == strategy)
            if since:
                query = query.filter(TradeRow.timestamp >= since)
            query = query.order_by(TradeRow.timestamp.desc()).limit(limit)

            return [self._row_to_dict(row) for row in query.all()]
        finally:
            session.close()

    def get_signals(self, strategy: Optional[str] = None,
                    limit: int = 200) -> List[dict]:
        """Get signals for dashboard analysis."""
        session = self.get_session()
        try:
            query = session.query(SignalRow)
            if strategy:
                if strategy == "GARBAGE_TIME":
                    query = query.filter(SignalRow.strategy.in_(_BOUNCEBACK_DB_VALUES))
                else:
                    query = query.filter(SignalRow.strategy == strategy)
            query = query.order_by(SignalRow.timestamp.desc()).limit(limit)
            return [self._row_to_dict(row) for row in query.all()]
        finally:
            session.close()

    def get_active_positions(self) -> List[dict]:
        """Get all active positions."""
        session = self.get_session()
        try:
            rows = session.query(PositionRow).filter(
                PositionRow.status.in_(["ACTIVE", "CAPITAL_RECOVERED"])
            ).all()
            return [self._row_to_dict(row) for row in rows]
        finally:
            session.close()

    def has_active_position(self, strategy: str, game_id: str) -> bool:
        """Check if an active position already exists for this strategy + game."""
        session = self.get_session()
        try:
            strat_filter = (
                PositionRow.strategy.in_(_BOUNCEBACK_DB_VALUES)
                if strategy == Strategy.GARBAGE_TIME.value
                else PositionRow.strategy == strategy
            )
            count = session.query(PositionRow).filter(
                strat_filter,
                PositionRow.game_id == game_id,
                PositionRow.status.in_(["ACTIVE", "CAPITAL_RECOVERED"]),
            ).count()
            return count > 0
        finally:
            session.close()

    def get_daily_performance(self, days: int = 30) -> List[dict]:
        """Get daily performance history."""
        session = self.get_session()
        try:
            rows = session.query(DailyPerformanceRow).order_by(
                DailyPerformanceRow.date.desc()
            ).limit(days * 3).all()  # 3 strategies per day
            return [self._row_to_dict(row) for row in rows]
        finally:
            session.close()

    def get_game_snapshots(self, game_id: str, limit: int = 500) -> List[dict]:
        """Get all snapshots for a specific game."""
        session = self.get_session()
        try:
            rows = session.query(GameSnapshotRow).filter_by(
                game_id=game_id
            ).order_by(GameSnapshotRow.timestamp).limit(limit).all()
            return [self._row_to_dict(row) for row in rows]
        finally:
            session.close()

    def get_all_trades_for_replay(self) -> List[dict]:
        """Get all trades ever, for bankroll reconstruction on restart."""
        session = self.get_session()
        try:
            rows = session.query(TradeRow).order_by(TradeRow.timestamp).all()
            return [self._row_to_dict(row) for row in rows]
        finally:
            session.close()

    def get_active_positions_full(self) -> List[dict]:
        """Get active positions with their trade history for state reconstruction."""
        session = self.get_session()
        try:
            positions = session.query(PositionRow).filter(
                PositionRow.status.in_(["ACTIVE", "CAPITAL_RECOVERED"])
            ).all()
            result = []
            for pos in positions:
                pos_dict = self._row_to_dict(pos)
                trades = session.query(TradeRow).filter_by(
                    position_id=pos.position_id
                ).order_by(TradeRow.timestamp).all()
                pos_dict["trades"] = [self._row_to_dict(t) for t in trades]
                result.append(pos_dict)
            return result
        finally:
            session.close()

    def get_strategy_stats(self, strategy: str) -> dict:
        """Calculate aggregate stats for a strategy."""
        session = self.get_session()
        try:
            if strategy == "GARBAGE_TIME":
                trades = session.query(TradeRow).filter(
                    TradeRow.strategy.in_(_BOUNCEBACK_DB_VALUES)
                ).all()
            else:
                trades = session.query(TradeRow).filter_by(strategy=strategy).all()

            wins = [t for t in trades if t.pnl_cents and t.pnl_cents > 0
                    and t.action in ("SELL_ALL", "SETTLED_WIN")]
            losses = [t for t in trades if t.pnl_cents and t.pnl_cents < 0
                      and t.action in ("SELL_ALL", "SETTLED_LOSS")]

            return {
                "total_trades": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": len(wins) / max(1, len(wins) + len(losses)),
                "total_pnl": sum(t.pnl_cents or 0 for t in trades),
                "avg_win": sum(t.pnl_cents for t in wins) / max(1, len(wins)),
                "avg_loss": sum(t.pnl_cents for t in losses) / max(1, len(losses)),
                "best_trade": max((t.pnl_cents or 0 for t in trades), default=0),
                "worst_trade": min((t.pnl_cents or 0 for t in trades), default=0),
            }
        finally:
            session.close()

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a SQLAlchemy row to a plain dict."""
        if row is None:
            return {}
        d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        if "strategy" in d and d["strategy"]:
            parsed = strategy_from_stored_value(str(d["strategy"]))
            if parsed is not None:
                d["strategy"] = parsed.value
        if "reason" in d and d["reason"]:
            r = str(d["reason"])
            if "Heavy Favorite" in r:
                d["reason"] = r.replace("Heavy Favorite", "Bounceback")
            elif "heavy favorite" in r:
                d["reason"] = r.replace("heavy favorite", "Bounceback")
        return d
