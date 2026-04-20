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
from telegram_utils import send_telegram_message, send_telegram_message_detailed


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


def _mask_secret(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


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
    """Send en enkel midlertidig testmelding ved oppstart."""
    message_html = (
        "🧪 <b>Crashbot startup-test</b>\n\n"
        "Boten er oppe og forsøker Telegram-send."
    )
    print("[TEST] Startup-test: sender enkel Telegram testmelding (STARTUP_TEST).")
    result = send_telegram_message_detailed(
        token_bot=token_bot,
        chat_id=chat_id,
        message_html=message_html,
        message_type="STARTUP_TEST",
    )
    print(
        f"[TEST] Startup-test respons: success={result.success} status={result.status_code} "
        f"body={result.response_snippet or '<empty>'} error={result.error or '<none>'}"
    )
    return result.success


def main() -> None:
    token_bot = os.getenv("TOKEN_BOT")
    chat_id = os.getenv("CHAT_ID")
    force_test_mode = _env_bool("CRASHBOT_FORCE_TEST", "false")
    ignore_market_hours = _env_bool("CRASHBOT_IGNORE_MARKET_HOURS", "false")
    raw_test_phase = os.getenv("CRASHBOT_TEST_PHASE", "CRASH_ALERT").strip().upper()
    test_send_once = _env_bool("CRASHBOT_TEST_SEND_ONCE", "true")

    print("[BOOT] Miljøvariabler lest ved oppstart:")
    print(f"        TOKEN_BOT={_mask_secret(token_bot)}")
    print(f"        CHAT_ID={_mask_secret(chat_id)}")
    print(f"        CRASHBOT_FORCE_TEST={'true' if force_test_mode else 'false'}")
    print(f"        CRASHBOT_IGNORE_MARKET_HOURS={'true' if ignore_market_hours else 'false'}")
    print(f"        CRASHBOT_TEST_PHASE={raw_test_phase}")
    print(f"        CRASHBOT_TEST_SEND_ONCE={'true' if test_send_once else 'false'}")

    if not token_bot or not chat_id:
        print("[BOOT] Mangler TOKEN_BOT eller CHAT_ID i miljøvariabler.")
        return

    if force_test_mode:
        print("[BOOT] Kjøremodus: TESTFLYT (CRASHBOT_FORCE_TEST=true).")
    else:
        print("[BOOT] Kjøremodus: NORMAL DRIFT (CRASHBOT_FORCE_TEST=false).")
        print("[BOOT] Merk: CRASHBOT_TEST_PHASE alene aktiverer ikke testflyt.")

    startup_test_sent = False
    if force_test_mode:
        if test_send_once and startup_test_sent:
            print("[TEST] Hopper over startup-test fordi CRASHBOT_TEST_SEND_ONCE=true og test allerede sendt.")
        else:
            print("[TEST] CRASHBOT_FORCE_TEST=true -> forsøker startup-testmelding.")
            sent = send_startup_test_message(token_bot=token_bot, chat_id=chat_id)
            startup_test_sent = sent or test_send_once
            if sent:
                print("[TEST] Startup-testmelding sendt OK.")
            else:
                print("[TEST] Startup-testmelding FEILET.")

    print(f"[BOOT] Crashbot startet for: {', '.join(WATCHLIST)}")
    valid_test_phases = {PHASE_CRASH_ALERT, PHASE_REBOUND_WATCH, PHASE_SETUP_ACTIVE, PHASE_COOL_OFF}

    while True:
        force_test_mode = _env_bool("CRASHBOT_FORCE_TEST", "false")
        ignore_market_hours = _env_bool("CRASHBOT_IGNORE_MARKET_HOURS", "false")
        raw_test_phase = os.getenv("CRASHBOT_TEST_PHASE", "CRASH_ALERT").strip().upper()
        test_phase = raw_test_phase
        if test_phase not in valid_test_phases:
            print(f"[WARN] Ugyldig CRASHBOT_TEST_PHASE='{raw_test_phase}'. Faller tilbake til CRASH_ALERT.")
            test_phase = PHASE_CRASH_ALERT
        test_send_once = _env_bool("CRASHBOT_TEST_SEND_ONCE", "true")

        within_window = True if force_test_mode or ignore_market_hours else is_market_hours()
        print("[LOOP] Testvariabler:")
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

            def _sender(message_html: str, message_type: str = "SIGNAL") -> bool:
                return send_telegram_message(
                    token_bot=token_bot,
                    chat_id=chat_id,
                    message_html=message_html,
                    message_type=message_type,
                )

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
