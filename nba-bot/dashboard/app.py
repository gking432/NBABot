"""
Dashboard API.
FastAPI backend that serves all data to the frontend.
Cursor: Build the frontend HTML/JS/CSS in templates.py using these endpoints.
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from datetime import datetime, timedelta
from typing import Optional


def create_app(bot) -> FastAPI:
    app = FastAPI(title="NBA Trading Bot Dashboard")

    # ─── API Endpoints (JSON) ───

    @app.get("/api/status")
    def get_status():
        """Full bot status: bankrolls, positions, risk, live games."""
        try:
            return bot.get_status()
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e), "detail": "Bot status failed"}
            )

    @app.get("/api/trades")
    def get_trades(strategy: Optional[str] = None, limit: int = 100):
        return bot.db.get_trades(strategy=strategy, limit=limit)

    @app.get("/api/signals")
    def get_signals(strategy: Optional[str] = None, limit: int = 200):
        return bot.db.get_signals(strategy=strategy, limit=limit)

    @app.get("/api/positions/active")
    def get_active_positions():
        return bot.db.get_active_positions()

    @app.get("/api/performance")
    def get_performance(days: int = 30):
        return bot.db.get_daily_performance(days=days)

    @app.get("/api/stats/{strategy}")
    def get_strategy_stats(strategy: str):
        return bot.db.get_strategy_stats(strategy)

    @app.get("/api/snapshots/{game_id}")
    def get_game_snapshots(game_id: str):
        return bot.db.get_game_snapshots(game_id)

    # ─── Frontend (HTML) ───

    @app.get("/")
    def dashboard():
        """Main dashboard page — no-store so the browser never serves stale HTML/JS."""
        try:
            from dashboard.templates import render_dashboard
            body = render_dashboard()
            return Response(
                content=body,
                media_type="text/html; charset=utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                },
            )
        except Exception as e:
            return HTMLResponse(
                content=f"<h1>Dashboard</h1><p>Template error: {e}</p><p>API available at /api/status</p>",
                headers={"Cache-Control": "no-store"},
            )

    return app
