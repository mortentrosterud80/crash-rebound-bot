"""Signalmotor og state-maskin for ELO Crash Rebound."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pytz
import yfinance as yf

from crash_formatter import (
    cool_off_message,
    crash_alert_message,
    follow_up_message,
    rebound_watch_message,
    setup_active_message,
    with_test_mode_banner,
)
from crash_rebound_config import (
    ALERT_TIMEZONE,
    MIN_ALERT_COOLDOWN_MINUTES,
    MIN_SETUP_RR,
    PHASE_COOL_OFF,
    PHASE_CRASH_ALERT,
    PHASE_IDLE,
    PHASE_REBOUND_WATCH,
    PHASE_SETUP_ACTIVE,
)
from news_utils import get_sentiment_snapshot
from state_utils import get_ticker_state, update_ticker_state

FOLLOW_UP_SLOTS = {
    "09:00": "last_sent_0900",
    "11:00": "last_sent_1100",
    "13:00": "last_sent_1300",
    "15:00": "last_sent_1500",
}


def now_oslo() -> datetime:
    return datetime.now(pytz.timezone(ALERT_TIMEZONE))


def _send_with_type(send_message, message_html: str, message_type: str) -> bool:
    try:
        return send_message(message_html, message_type)
    except TypeError:
        return send_message(message_html)


def _build_test_metrics(phase: str) -> dict[str, Any]:
    datasets: dict[str, dict[str, Any]] = {
        PHASE_CRASH_ALERT: {
            "last_price": 38.10,
            "day_change_pct": -19.8,
            "pct_5d": -21.4,
            "volume_ratio": 2.6,
            "day_low": 37.40,
            "day_high": 41.20,
            "previous_close": 47.51,
        },
        PHASE_REBOUND_WATCH: {
            "last_price": 37.80,
            "day_change_pct": -1.2,
            "pct_5d": -20.5,
            "volume_ratio": 1.1,
            "day_low": 37.30,
            "day_high": 38.40,
            "previous_close": 38.26,
        },
        PHASE_SETUP_ACTIVE: {
            "last_price": 39.40,
            "day_change_pct": 4.1,
            "pct_5d": -14.0,
            "volume_ratio": 1.8,
            "day_low": 39.10,
            "day_high": 40.00,
            "previous_close": 37.85,
        },
        PHASE_COOL_OFF: {
            "last_price": 40.10,
            "day_change_pct": 0.4,
            "pct_5d": -8.0,
            "volume_ratio": 0.9,
            "day_low": 39.70,
            "day_high": 40.30,
            "previous_close": 39.94,
        },
    }
    return datasets.get(phase, datasets[PHASE_CRASH_ALERT]).copy()


def _calc_rsi14(close: pd.Series) -> float | None:
    if len(close) < 15:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    return float(value) if pd.notna(value) else None


def _calc_atr14(df: pd.DataFrame) -> float | None:
    if len(df) < 15:
        return None
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    return float(atr) if pd.notna(atr) else None


def fetch_market_data(symbol: str) -> dict[str, Any] | None:
    try:
        ticker = yf.Ticker(symbol)
        daily = ticker.history(period="6mo", interval="1d", auto_adjust=False).dropna(how="all")
        intraday = ticker.history(period="5d", interval="30m", auto_adjust=False).dropna(how="all")
        if daily.empty or len(daily) < 6:
            return None

        last_price = float(daily.iloc[-1]["Close"])
        day_high = float(daily.iloc[-1]["High"])
        day_low = float(daily.iloc[-1]["Low"])
        day_volume = float(daily.iloc[-1]["Volume"])
        day_open = float(daily.iloc[-1]["Open"])

        if not intraday.empty:
            idx = intraday.index
            if getattr(idx, "tz", None) is not None:
                idx = idx.tz_convert(ALERT_TIMEZONE)
            today = now_oslo().date()
            today_data = intraday[idx.date == today]
            if not today_data.empty:
                last_price = float(today_data.iloc[-1]["Close"])
                day_high = float(today_data["High"].max())
                day_low = float(today_data["Low"].min())
                day_volume = float(today_data["Volume"].sum())
                day_open = float(today_data.iloc[0]["Open"])

        previous_close = float(daily.iloc[-2]["Close"])
        day_change_pct = ((last_price / previous_close) - 1) * 100 if previous_close else 0.0
        from_open_pct = ((last_price / day_open) - 1) * 100 if day_open else 0.0

        close_series = daily["Close"].copy()
        close_series.iloc[-1] = last_price

        pct_3d = ((last_price / float(close_series.iloc[-4])) - 1) * 100 if len(close_series) >= 4 else None
        pct_5d = ((last_price / float(close_series.iloc[-6])) - 1) * 100 if len(close_series) >= 6 else None

        avg_volume_20d = float(daily["Volume"].iloc[-21:-1].mean()) if len(daily) >= 21 else float(daily["Volume"].iloc[:-1].mean())
        volume_ratio = (day_volume / avg_volume_20d) if avg_volume_20d and avg_volume_20d > 0 else 0.0

        rsi14 = _calc_rsi14(close_series)
        atr14 = _calc_atr14(daily)

        return {
            "last_price": last_price,
            "previous_close": previous_close,
            "day_change_pct": day_change_pct,
            "from_open_pct": from_open_pct,
            "pct_3d": pct_3d,
            "pct_5d": pct_5d,
            "day_volume": day_volume,
            "avg_volume_20d": avg_volume_20d,
            "volume_ratio": volume_ratio,
            "day_low": day_low,
            "day_high": day_high,
            "day_open": day_open,
            "rsi14": rsi14,
            "atr14": atr14,
        }
    except Exception as exc:
        print(f"[DATA] Feil ved henting for {symbol}: {exc}")
        return None


def _minutes_since(ts_iso: str | None) -> float | None:
    if not ts_iso:
        return None
    try:
        then = datetime.fromisoformat(ts_iso)
        if then.tzinfo is None:
            then = pytz.utc.localize(then)
        return (datetime.now(pytz.utc) - then.astimezone(pytz.utc)).total_seconds() / 60
    except Exception:
        return None


def _crash_trigger(metrics: dict) -> tuple[bool, list[str]]:
    day = metrics["day_change_pct"]
    vr = metrics["volume_ratio"]
    d3 = metrics.get("pct_3d")
    d5 = metrics.get("pct_5d")

    trigger = (
        (day <= -8.0)
        or (day <= -5.0 and vr >= 1.8)
        or ((d3 is not None and d3 <= -12.0) or (d5 is not None and d5 <= -16.0))
    )
    if not trigger:
        return False, []

    lines: list[str] = ["Kraftig nyhetsdrevet reaksjon mistenkes", "Uvanlig stort salgsvolum"]
    if day <= -8.0:
        lines.append("Unormalt stort dagsfall")
    if d3 is not None and d3 <= -12.0:
        lines.append("Bratt 3-dagers nedgang")
    return True, lines[:3]


def _stabilizing(metrics: dict, ticker_state: dict) -> tuple[bool, list[str]]:
    panic_low = ticker_state.get("panic_low")
    if not panic_low:
        return False, []
    last = metrics["last_price"]
    day_low = metrics["day_low"]
    day_change = metrics["day_change_pct"]
    vr = metrics["volume_ratio"]

    cond_holds = last >= panic_low * 1.01 and day_low >= panic_low * 0.995
    cond_calmer = day_change > -2.0
    cond_volume = vr <= 1.6

    ok = cond_holds and (cond_calmer or cond_volume)
    obs = []
    if cond_volume:
        obs.append("Selgerpress avtar")
    if cond_holds:
        obs.append("Holder over intradag low fra crashfasen")
    if cond_calmer:
        obs.append("Kursfallet flater ut")
    if not obs:
        obs = ["Stabilisering er ikke bekreftet enda"]
    return ok, obs


def _build_setup(metrics: dict, ticker_state: dict) -> dict[str, float] | None:
    panic_low = float(ticker_state.get("panic_low") or 0)
    base_low = float(ticker_state.get("base_low") or panic_low)
    if panic_low <= 0:
        return None

    last = float(metrics["last_price"])
    previous_close = float(metrics["previous_close"])
    atr14 = float(metrics.get("atr14") or 0)

    entry_low = last * 0.995
    entry_high = last * 1.01
    entry_mid = (entry_low + entry_high) / 2

    buffer = max(atr14 * 0.35, last * 0.008)
    structural_low = min(panic_low, base_low)
    stop = structural_low - buffer
    risk = entry_mid - stop
    if risk <= 0:
        return None

    target_1 = max(entry_mid + risk * 2.0, previous_close * 0.97)
    target_2 = max(entry_mid + risk * 3.0, previous_close)
    rr_to_t1 = (target_1 - entry_mid) / risk

    return {
        "entry_low": round(entry_low, 2),
        "entry_high": round(entry_high, 2),
        "stop": round(stop, 2),
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "rr_to_t1": round(rr_to_t1, 2),
    }


def _setup_ready(metrics: dict, ticker_state: dict) -> tuple[bool, list[str], dict[str, float] | None]:
    panic_low = float(ticker_state.get("panic_low") or 0)
    if panic_low <= 0:
        return False, [], None

    cond_green = metrics["day_change_pct"] >= 3.0
    cond_above = metrics["last_price"] >= panic_low * 1.03
    cond_volume = metrics["volume_ratio"] >= 1.0
    cond_higher_low = metrics["day_low"] > panic_low * 1.005

    setup = _build_setup(metrics, ticker_state)
    if not setup:
        return False, [], None

    rr_ok = setup["rr_to_t1"] >= MIN_SETUP_RR
    ready = cond_green and cond_above and cond_higher_low and rr_ok and cond_volume

    triggers = []
    if cond_green:
        triggers.append("Første sterke grønne dag")
    if cond_higher_low:
        triggers.append("Higher low etablert")
    if cond_volume:
        triggers.append("Volum støtter oppgang")

    return ready, triggers[:3], setup


def _cool_off_reason(metrics: dict, ticker_state: dict) -> str | None:
    panic_low = ticker_state.get("panic_low")
    if panic_low and metrics["last_price"] < panic_low * 0.995:
        return "Ny dump har ødelagt strukturen etter crash-fasen."

    if ticker_state.get("phase") == PHASE_SETUP_ACTIVE and metrics["day_change_pct"] < -3.0:
        return "Rebound-case mistet momentum etter aktiv setup."

    if ticker_state.get("phase") == PHASE_REBOUND_WATCH and abs(metrics["day_change_pct"]) < 0.8 and metrics["volume_ratio"] < 0.8:
        return "Caset har glidd over i sidelengs drift uten tydelig edge."
    return None


def _event_day_number(event_start_date: str | None) -> int:
    if not event_start_date:
        return 0
    try:
        start = datetime.fromisoformat(event_start_date).date()
        return max(0, (now_oslo().date() - start).days)
    except Exception:
        return 0


def _status_label(metrics: dict, ticker_state: dict, sentiment_bucket: str) -> str:
    panic_low = ticker_state.get("panic_low")
    if panic_low and metrics.get("last_price", 0.0) < panic_low:
        return "🔴 Svekkes igjen"

    if metrics.get("from_open_pct", 0.0) >= 1.2 and metrics.get("volume_ratio", 0.0) >= 1.0 and sentiment_bucket in {"Bedrende", "Positivt"}:
        return "🟢 Bedrer seg"

    if sentiment_bucket in {"Negativt", "Svakt negativt"} and metrics.get("from_open_pct", 0.0) < 0:
        return "🔴 Svekkes igjen"

    return "🟡 Stabiliserer seg"


def _follow_up_slot(now: datetime) -> tuple[str, str] | None:
    hhmm = now.strftime("%H:%M")
    if hhmm in FOLLOW_UP_SLOTS:
        return hhmm, FOLLOW_UP_SLOTS[hhmm]
    return None


def _send_follow_up_if_due(symbol: str, meta: dict, ticker_state: dict, metrics: dict, can_send_alerts: bool, send_message, sentiment) -> dict[str, Any] | None:
    if not can_send_alerts:
        print(f"[FLOW] Follow-up blokkert av market-hours for {symbol}.")
        return None
    if not ticker_state.get("active_followup"):
        print(f"[FLOW] Follow-up ikke aktiv for {symbol}.")
        return None

    day_number = _event_day_number(ticker_state.get("followup_start_date"))
    if day_number > 3:
        print(f"[FLOW] Follow-up avsluttes for {symbol} (day_number={day_number}).")
        return {"active_followup": False, "followup_day_number": day_number}

    slot_info = _follow_up_slot(now_oslo())
    if not slot_info:
        print(f"[FLOW] Ingen follow-up slot nå for {symbol}.")
        return {"followup_day_number": day_number}

    _, state_key = slot_info
    today = now_oslo().date().isoformat()
    if ticker_state.get(state_key) == today:
        print(f"[FLOW] Duplicate-block follow-up for {symbol}: {state_key} allerede sendt i dag.")
        return {"followup_day_number": day_number}

    status_label = _status_label(metrics, ticker_state, sentiment.sentiment)
    followup_metrics = {**metrics, "panic_low": ticker_state.get("panic_low")}
    message_html = follow_up_message(
        symbol=symbol,
        name=meta["name"],
        metrics=followup_metrics,
        now_oslo=now_oslo(),
        day_number=day_number,
        status_label=status_label,
        sentiment_commentary=sentiment.commentary,
    )

    print(f"[FLOW] Besluttet å sende FOLLOW_UP for {symbol}.")
    if _send_with_type(send_message, message_html, "FOLLOW_UP"):
        return {
            state_key: today,
            "followup_day_number": day_number,
            "last_message_type": "FOLLOW_UP",
            "last_message_ts": datetime.now(pytz.utc).isoformat(),
            "last_sentiment": sentiment.sentiment,
            "last_news_cause": sentiment.cause,
        }

    return {"followup_day_number": day_number}


def evaluate_ticker(
    symbol: str,
    meta: dict,
    state: dict,
    can_send_alerts: bool,
    send_message,
    force_test_mode: bool = False,
    test_phase: str | None = None,
    test_send_once: bool = True,
) -> dict:
    if force_test_mode:
        print(f"[FLOW] {symbol}: kjører testflyt (force_test_mode=true).")
        phase = test_phase if test_phase in {PHASE_CRASH_ALERT, PHASE_REBOUND_WATCH, PHASE_SETUP_ACTIVE, PHASE_COOL_OFF} else PHASE_CRASH_ALERT
        ticker_state = get_ticker_state(state, symbol)
        if test_send_once and ticker_state.get("last_test_phase_sent") == phase:
            print(f"[TEST] State-blokkering: hopper over testmelding fordi fase {phase} allerede er sendt og send_once=True")
            return state

        metrics = _build_test_metrics(phase)
        alert_now = now_oslo()
        print(f"[TEST] Bruker testdata for {symbol} i fase {phase}")
        if phase == PHASE_CRASH_ALERT:
            trigger_lines = ["Kraftig nyhetsdrevet reaksjon mistenkes"]
            message_html = crash_alert_message(symbol, meta["name"], metrics, alert_now, trigger_lines)
        elif phase == PHASE_REBOUND_WATCH:
            observations = ["Selgerpress avtar", "Holder over intradag low fra i går", "Volum normaliseres"]
            message_html = rebound_watch_message(symbol, meta["name"], metrics, alert_now, 1, observations)
        elif phase == PHASE_SETUP_ACTIVE:
            setup = {
                "entry_low": 39.20,
                "entry_high": 39.80,
                "stop": 36.90,
                "target_1": 42.00,
                "target_2": 44.00,
                "rr_to_t1": 2.0,
            }
            triggers = ["Første sterke grønne dag", "Higher low etablert", "Volum støtter oppgang"]
            message_html = setup_active_message(symbol, meta["name"], metrics, alert_now, 1, setup, triggers)
        else:
            reason = "Testfase for COOL OFF."
            message_html = cool_off_message(symbol, meta["name"], metrics, alert_now, reason)

        print(f"[TEST] Sender Telegram testmelding for fase {phase}")
        sent_ok = _send_with_type(send_message, with_test_mode_banner(message_html), f"TEST_{phase}")
        if sent_ok:
            state = update_ticker_state(
                state,
                symbol,
                {
                    "phase": phase,
                    "last_message_type": phase,
                    "last_message_ts": datetime.now(pytz.utc).isoformat(),
                    "last_test_phase_sent": phase,
                    "last_test_sent_at": datetime.now(pytz.utc).isoformat(),
                    "last_price": round(metrics["last_price"], 4),
                    "last_day_change_pct": round(metrics["day_change_pct"], 4),
                },
            )
        else:
            print(f"[ERROR] Telegram testmelding feilet for fase {phase}")
        return state

    print(f"[FLOW] {symbol}: kjører normal signalflyt.")
    metrics = fetch_market_data(symbol)
    if not metrics:
        print(f"[FLOW] Manglende data for {symbol}, ingen signalvurdering denne runden.")
        return state

    ticker_state = get_ticker_state(state, symbol)
    current_phase = ticker_state.get("phase", PHASE_IDLE)
    alert_now = now_oslo()
    today = alert_now.date().isoformat()
    sentiment = get_sentiment_snapshot(symbol)

    state = update_ticker_state(
        state,
        symbol,
        {
            "last_price": round(metrics["last_price"], 4),
            "last_day_change_pct": round(metrics["day_change_pct"], 4),
            "base_low": round(min(metrics["day_low"], ticker_state.get("base_low") or metrics["day_low"]), 4),
            "last_sentiment": sentiment.sentiment,
            "last_news_cause": sentiment.cause,
        },
    )
    ticker_state = get_ticker_state(state, symbol)

    crash_hit, trigger_lines = _crash_trigger(metrics)
    if not crash_hit:
        print(f"[FLOW] Trigger ikke oppfylt for {symbol} (ingen crash-trigger).")
    stabilizing, observations = _stabilizing(metrics, ticker_state)
    setup_ready, setup_triggers, setup = _setup_ready(metrics, ticker_state)
    cool_reason = _cool_off_reason(metrics, ticker_state)

    next_phase = current_phase
    message_type = None
    message_html = None

    if crash_hit and current_phase in {PHASE_IDLE, PHASE_COOL_OFF}:
        print(f"[FLOW] {symbol}: crash-trigger oppfylt i fase {current_phase} -> {PHASE_CRASH_ALERT}.")
        next_phase = PHASE_CRASH_ALERT
        message_type = PHASE_CRASH_ALERT
        message_html = crash_alert_message(symbol, meta["name"], metrics, alert_now, trigger_lines, sentiment.commentary)
        state = update_ticker_state(
            state,
            symbol,
            {
                "panic_low": round(metrics["day_low"], 4),
                "panic_high": round(metrics["day_high"], 4),
                "event_start_date": today,
                "followup_start_date": today,
                "followup_day_number": 0,
                "active_followup": True,
                "setup_sent": False,
                "last_alert_change_pct": round(metrics["day_change_pct"], 4),
                "last_sent_0900": None,
                "last_sent_1100": None,
                "last_sent_1300": None,
                "last_sent_1500": None,
            },
        )

    elif current_phase == PHASE_CRASH_ALERT and stabilizing:
        print(f"[FLOW] {symbol}: stabilisering bekreftet -> {PHASE_REBOUND_WATCH}.")
        next_phase = PHASE_REBOUND_WATCH
        message_type = PHASE_REBOUND_WATCH
        day_number = _event_day_number(ticker_state.get("event_start_date"))
        message_html = rebound_watch_message(symbol, meta["name"], metrics, alert_now, day_number, observations, sentiment.commentary)

    elif current_phase == PHASE_REBOUND_WATCH and setup_ready and setup and not ticker_state.get("setup_sent"):
        print(f"[FLOW] {symbol}: setup trigger oppfylt -> {PHASE_SETUP_ACTIVE}.")
        next_phase = PHASE_SETUP_ACTIVE
        message_type = PHASE_SETUP_ACTIVE
        day_number = _event_day_number(ticker_state.get("event_start_date"))
        message_html = setup_active_message(symbol, meta["name"], metrics, alert_now, day_number, setup, setup_triggers)

    elif current_phase in {PHASE_REBOUND_WATCH, PHASE_SETUP_ACTIVE} and cool_reason:
        print(f"[FLOW] {symbol}: cool-off grunn funnet -> {PHASE_COOL_OFF}.")
        next_phase = PHASE_COOL_OFF
        message_type = PHASE_COOL_OFF
        message_html = cool_off_message(symbol, meta["name"], metrics, alert_now, cool_reason)
        state = update_ticker_state(state, symbol, {"active_followup": False})

    elif current_phase == PHASE_CRASH_ALERT and crash_hit:
        last_alert_change = ticker_state.get("last_alert_change_pct")
        if last_alert_change is not None and metrics["day_change_pct"] <= float(last_alert_change) - 3.0:
            message_type = PHASE_CRASH_ALERT
            message_html = crash_alert_message(symbol, meta["name"], metrics, alert_now, trigger_lines, sentiment.commentary)
            state = update_ticker_state(state, symbol, {"last_alert_change_pct": round(metrics["day_change_pct"], 4)})

    if message_type and message_html and not can_send_alerts:
        print(f"[FLOW] Market-hours blokkering for {symbol}: message_type={message_type} ble ikke sendt.")

    if message_type and message_html and can_send_alerts:
        print(f"[FLOW] Vurderer sending for {symbol}: message_type={message_type}, current_phase={current_phase}, next_phase={next_phase}.")
        same_type = message_type == ticker_state.get("last_message_type")
        mins_since = _minutes_since(ticker_state.get("last_message_ts"))
        cooled_down = (mins_since is None) or (mins_since >= MIN_ALERT_COOLDOWN_MINUTES)
        phase_change = next_phase != current_phase
        if phase_change or (not same_type) or cooled_down:
            print(f"[FLOW] Besluttet å sende alert for {symbol}: {message_type}.")
            if _send_with_type(send_message, message_html, message_type):
                updates = {
                    "phase": next_phase,
                    "last_message_type": message_type,
                    "last_message_ts": datetime.now(pytz.utc).isoformat(),
                }
                if message_type == PHASE_REBOUND_WATCH:
                    updates["rebound_watch_started_at"] = datetime.now(pytz.utc).isoformat()
                if message_type == PHASE_SETUP_ACTIVE:
                    updates["setup_sent"] = True
                state = update_ticker_state(state, symbol, updates)
            else:
                print(f"[FLOW] Telegram-send feilet for {symbol}: {message_type}.")
        else:
            reasons: list[str] = []
            if same_type:
                reasons.append("duplicate-block (samme meldingstype)")
            if not cooled_down:
                reasons.append(f"cooldown/state blokkering ({mins_since:.1f}m < {MIN_ALERT_COOLDOWN_MINUTES}m)")
            print(f"[FLOW] State blokkerer ny sending for {symbol}: {', '.join(reasons)}")

    ticker_state = get_ticker_state(state, symbol)
    followup_updates = _send_follow_up_if_due(symbol, meta, ticker_state, metrics, can_send_alerts, send_message, sentiment)
    if followup_updates:
        state = update_ticker_state(state, symbol, followup_updates)

    return state
