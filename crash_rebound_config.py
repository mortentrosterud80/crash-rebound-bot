"""Konfigurasjon for Crash Rebound-boten."""

ALERT_TIMEZONE = "Europe/Oslo"
ALERT_WINDOW_START = "09:00"
ALERT_WINDOW_END = "16:30"
CHECK_INTERVAL_SECONDS = 15 * 60
FORCE_TEST_MESSAGE = True

STATE_FILE_PATH = "data/crash_rebound_state.json"

CRASH_WATCHLIST = {
    "ELO.OL": {
        "name": "Elopak",
        "emoji": "🧃",
        "enabled": True,
        "crash_drop_pct": -12.0,
        "intraday_crash_pct": -10.0,
        "volume_ratio_min": 1.8,
        "rebound_confirm_pct": 3.0,
    }
}

DEFAULT_TICKER_STATE = {
    "status": "IDLE",  # IDLE | WATCH
    "crash_date": None,
    "panic_low": None,
    "last_price": None,
    "last_day_change_pct": None,
    "last_signal": None,
    "updated_at": None,
    "crash_alert_sent_date": None,
    "rebound_watch_sent_date": None,
    "setup_sent_date": None,
}
