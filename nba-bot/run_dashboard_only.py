"""
Run ONLY the dashboard — no bot main loop.
Use this to preview the dashboard without API keys or live trading.
Dashboard runs on port 8001 (to avoid conflict with full bot on 8000).
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
)
# Suppress noisy loggers
logging.getLogger("data.kalshi_client").setLevel(logging.ERROR)
logging.getLogger("data.odds_client").setLevel(logging.ERROR)

from core.bot import TradingBot
from dashboard.app import create_app
import uvicorn

if __name__ == "__main__":
    print("Starting dashboard (no bot loop)...")
    print("Open http://localhost:8001 in your browser")
    print("Press Ctrl+C to stop\n")
    bot = TradingBot()
    try:
        bot.initialize()
    except Exception as e:
        print(f"Note: Bot init had issues (expected without API keys): {e}")
    app = create_app(bot)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
