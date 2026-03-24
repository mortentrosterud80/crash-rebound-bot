"""Runner for crashbot (separat fra swingbot)."""

from __future__ import annotations

import os
import time
from datetime import datetime

import pytz

from crash_detector import evaluate_ticker
from crash_rebound_config import (
    ALERT_TIMEZONE,
    ALERT_WINDOW_END,
    ALERT_WINDOW_START,
    CHECK_INTERVAL_SECONDS,
    TICKER_META,
    WATCHLIST,
)
from state_utils import load_state, save_state
from telegram_utils import send_telegram_message


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def is_market_hours() -> bool:
    tz = pytz.timezone(ALERT_TIMEZONE)
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False

    start_h, start_m = _parse_hhmm(ALERT_WINDOW_START)
    end_h, end_m = _parse_hhmm(ALERT_WINDOW_END)
    now_minutes = now.hour * 60 + now.minute
    return (start_h * 60 + start_m) <= now_minutes <= (end_h * 60 + end_m)


def main() -> None:
    token_bot = os.getenv("TOKEN_BOT")
    chat_id = os.getenv("CHAT_ID")
    if not token_bot or not chat_id:
        print("[BOOT] Mangler TOKEN_BOT eller CHAT_ID i miljøvariabler.")
        return

    print(f"[BOOT] Crashbot startet for: {', '.join(WATCHLIST)}")

    while True:
        within_window = is_market_hours()
        state = load_state()

        for symbol in WATCHLIST:
            meta = TICKER_META.get(symbol, {"name": symbol, "emoji": "🧃"})

            def _sender(message_html: str) -> bool:
                return send_telegram_message(token_bot=token_bot, chat_id=chat_id, message_html=message_html)

            state = evaluate_ticker(
                symbol=symbol,
                meta=meta,
                state=state,
                can_send_alerts=within_window,
                send_message=_sender,
            )

        save_state(state)
        print(f"[LOOP] Syklus ferdig. market_hours={within_window}. Sover {CHECK_INTERVAL_SECONDS}s")
        time.sleep(CHECK_INTERVAL_SECONDS)
