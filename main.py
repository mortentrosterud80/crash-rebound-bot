"""Entry point for Crash Rebound Telegram-bot."""

from __future__ import annotations

import os
import time
from datetime import datetime

import pytz

from crash_rebound import evaluate_ticker
from crash_rebound_config import (
    ALERT_TIMEZONE,
    ALERT_WINDOW_END,
    ALERT_WINDOW_START,
    CHECK_INTERVAL_SECONDS,
    CRASH_WATCHLIST,
)
from state_utils import load_state, save_state
from telegram_utils import send_telegram_message


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def is_within_alert_window() -> bool:
    tz = pytz.timezone(ALERT_TIMEZONE)
    now = datetime.now(tz)

    start_h, start_m = _parse_hhmm(ALERT_WINDOW_START)
    end_h, end_m = _parse_hhmm(ALERT_WINDOW_END)

    now_minutes = now.hour * 60 + now.minute
    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m
    return start_minutes <= now_minutes <= end_minutes


def main() -> None:
    token_bot = os.getenv("TOKEN_BOT")
    chat_id = os.getenv("CHAT_ID")

    if not token_bot or not chat_id:
        print("[BOOT] Mangler TOKEN_BOT eller CHAT_ID i miljøvariabler. Stopper.")
        return

    print("[BOOT] Crash Rebound-bot starter.")
    print(f"[BOOT] Tickere i watchlist: {', '.join([s for s, m in CRASH_WATCHLIST.items() if m.get('enabled')])}")

    while True:
        within_window = is_within_alert_window()
        if within_window:
            print("[LOOP] Innenfor alert-vindu (Europe/Oslo).")
        else:
            print("[LOOP] Utenfor alert-vindu - evaluerer data men sender ikke meldinger.")

        state = load_state()

        for symbol, meta in CRASH_WATCHLIST.items():
            if not meta.get("enabled", True):
                continue

            def _sender(message_html: str) -> bool:
                return send_telegram_message(token_bot=token_bot, chat_id=chat_id, message_html=message_html)

            try:
                state = evaluate_ticker(
                    symbol=symbol,
                    meta=meta,
                    state=state,
                    can_send_alerts=within_window,
                    send_message=_sender,
                )
            except Exception as exc:
                print(f"[LOOP] Uventet feil i evaluering av {symbol}: {exc}")

        save_state(state)
        print(f"[LOOP] Ferdig syklus. Sover {CHECK_INTERVAL_SECONDS} sekunder.")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
