"""Entry point for the NBA Trading Bot."""
import logging
import sys
import os
import atexit
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import LOG_LEVEL, DASHBOARD_PORT

PID_FILE = "/tmp/nba_trading_bot.pid"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_lock():
    """Ensure only one bot instance runs at a time."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if _is_pid_alive(old_pid):
                print(f"ERROR: Another bot instance is already running (PID {old_pid}).")
                print(f"Kill it first: kill {old_pid}")
                sys.exit(1)
            else:
                os.remove(PID_FILE)
        except (ValueError, IOError):
            os.remove(PID_FILE)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    atexit.register(release_lock)


def release_lock():
    """Remove the PID file on exit."""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                stored_pid = int(f.read().strip())
            if stored_pid == os.getpid():
                os.remove(PID_FILE)
    except (ValueError, IOError):
        pass


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/bot.log"),
        ],
    )


def start_dashboard(bot):
    """Start the dashboard in a background thread."""
    try:
        from dashboard.app import create_app
        import uvicorn
        app = create_app(bot)
        uvicorn.run(app, host="0.0.0.0", port=DASHBOARD_PORT, log_level="warning")
    except Exception as e:
        logging.error(f"Dashboard failed to start: {e}")


def main():
    acquire_lock()
    setup_logging()

    from core.bot import TradingBot
    bot = TradingBot()

    # Start dashboard in background thread
    dash_thread = threading.Thread(target=start_dashboard, args=(bot,), daemon=True)
    dash_thread.start()
    logging.info(f"Dashboard starting at http://localhost:{DASHBOARD_PORT}")

    # Run the bot (blocking)
    bot.run()


if __name__ == "__main__":
    main()
