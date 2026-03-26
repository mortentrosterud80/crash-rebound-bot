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
    PHASE_COOL_OFF,
    PHASE_CRASH_ALERT,
    PHASE_REBOUND_WATCH,
    PHASE_SETUP_ACTIVE,
    TICKER_META,
    WATCHLIST,
)
from state_utils import get_ticker_state, load_state, save_state, update_ticker_state
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


def send_startup_test_message(token_bot: str, chat_id: str) -> bool:
    """Send en midlertidig testmelding ved oppstart."""
    message_html = (
        "📍 <b>TEST — OPPFØLGING (11:00)</b>\n\n"
        "🧃 <b>ELO.OL</b> (Elopak)\n"
        "💰 Kurs: <b>37,80 NOK</b>\n"
        "📈 Fra open: <b>+1,2 %</b>\n"
        "📊 Volum: <b>1.4x</b> normal\n"
        "🩸 Panikkbunn: <b>36,00 NOK</b>\n\n"
        "📰 <b>Stemning nå:</b>\n"
        "Fortsatt forsiktig, men mindre panikk enn i går.\n\n"
        "📍 <b>Status nå:</b>\n"
        "🟡 Stabiliserer seg\n\n"
        "🎯 <b>Hva ser vi etter:</b>\n"
        "• Holder over panikkbunn\n"
        "• Bedre volum og grønn styrke\n"
        "• Ingen nye negative signaler"
    )
    return send_telegram_message(token_bot=token_bot, chat_id=chat_id, message_html=message_html)


def main() -> None:
    token_bot = os.getenv("TOKEN_BOT")
    chat_id = os.getenv("CHAT_ID")
    if not token_bot or not chat_id:
        print("[BOOT] Mangler TOKEN_BOT eller CHAT_ID i miljøvariabler.")
        return

    send_startup_test = os.getenv("CRASHBOT_SEND_TEST_MESSAGE", "false").strip().lower() == "true"
    if send_startup_test:
        print("[TEST] Sender testmelding til Telegram")
        send_startup_test_message(token_bot=token_bot, chat_id=chat_id)

    print(f"[BOOT] Crashbot startet for: {', '.join(WATCHLIST)}")
    valid_test_phases = {PHASE_CRASH_ALERT, PHASE_REBOUND_WATCH, PHASE_SETUP_ACTIVE, PHASE_COOL_OFF}

    while True:
        force_test_mode = os.getenv("CRASHBOT_FORCE_TEST", "false").strip().lower() == "true"
        ignore_market_hours = os.getenv("CRASHBOT_IGNORE_MARKET_HOURS", "false").strip().lower() == "true"
        raw_test_phase = os.getenv("CRASHBOT_TEST_PHASE", "CRASH_ALERT").strip().upper()
        test_phase = raw_test_phase
        if test_phase not in valid_test_phases:
            print(f"[WARN] Ugyldig CRASHBOT_TEST_PHASE='{raw_test_phase}'. Faller tilbake til CRASH_ALERT.")
            test_phase = PHASE_CRASH_ALERT
        test_send_once = os.getenv("CRASHBOT_TEST_SEND_ONCE", "true").strip().lower() == "true"

        within_window = True if force_test_mode or ignore_market_hours else is_market_hours()
        print("[BOOT] Testvariabler:")
        print(f"        CRASHBOT_FORCE_TEST={'true' if force_test_mode else 'false'}")
        print(f"        CRASHBOT_IGNORE_MARKET_HOURS={'true' if ignore_market_hours else 'false'}")
        print(f"        CRASHBOT_TEST_PHASE={test_phase}")
        print(f"        CRASHBOT_TEST_SEND_ONCE={'true' if test_send_once else 'false'}")
        print(
            f"[DEBUG] force_test={force_test_mode} ignore_market_hours={ignore_market_hours} test_phase={test_phase} "
            f"send_once={test_send_once} market_hours={within_window}"
        )
        if force_test_mode:
            print(f"[TEST] Testmodus aktivert. Bypasser market hours og bruker testfase: {test_phase}")
            print("[TEST] Market hours bypass aktiv.")
        elif ignore_market_hours:
            print("[TEST] CRASHBOT_IGNORE_MARKET_HOURS=true. Bypasser market hours, men kjører normal logikk.")
        else:
            print("[DEBUG] Testmodus er IKKE aktiv. Kjører normal market-hours logikk.")
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
                force_test_mode=force_test_mode,
                test_phase=test_phase,
                test_send_once=test_send_once,
            )

            if not force_test_mode:
                ticker_state = get_ticker_state(state, symbol)
                if ticker_state.get("last_test_phase_sent") is not None:
                    print(f"[DEBUG] Testmodus avslått. Nullstiller last_test_phase_sent for {symbol}.")
                    state = update_ticker_state(
                        state,
                        symbol,
                        {
                            "last_test_phase_sent": None,
                            "last_test_sent_at": None,
                        },
                    )

        save_state(state)
        print(
            f"[LOOP] Syklus ferdig. market_hours={within_window} force_test={force_test_mode} "
            f"test_phase={test_phase} send_once={test_send_once}. Sover {CHECK_INTERVAL_SECONDS}s"
        )
        time.sleep(CHECK_INTERVAL_SECONDS)
