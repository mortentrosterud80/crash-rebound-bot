"""Konfigurasjon for ELO Crash Rebound-bot (v1)."""

ALERT_TIMEZONE = "Europe/Oslo"
ALERT_WINDOW_START = "09:00"
ALERT_WINDOW_END = "16:30"
CHECK_INTERVAL_SECONDS = 15 * 60

STATE_FILE_PATH = "data/crash_state.json"

WATCHLIST = ["ELO.OL"]
TICKER_META = {
    "ELO.OL": {
        "name": "Elopak",
        "emoji": "🧃",
    }
}

PHASE_IDLE = "IDLE"
PHASE_CRASH_ALERT = "CRASH_ALERT"
PHASE_REBOUND_WATCH = "REBOUND_WATCH"
PHASE_SETUP_ACTIVE = "SETUP_ACTIVE"
PHASE_COOL_OFF = "COOL_OFF"

PHASES = {
    PHASE_IDLE,
    PHASE_CRASH_ALERT,
    PHASE_REBOUND_WATCH,
    PHASE_SETUP_ACTIVE,
    PHASE_COOL_OFF,
}

MIN_ALERT_COOLDOWN_MINUTES = 30
MIN_SETUP_RR = 1.8

DEFAULT_TICKER_STATE = {
    "phase": PHASE_IDLE,
    "last_message_type": None,
    "last_message_ts": None,
    "last_price": None,
    "last_day_change_pct": None,
    "panic_low": None,
    "event_start_date": None,
    "base_low": None,
    "setup_sent": False,
    "rebound_watch_started_at": None,
    "last_alert_change_pct": None,
    "updated_at": None,
}
