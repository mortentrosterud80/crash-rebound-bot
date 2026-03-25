"""Kjernelogikk for Crash Rebound-strategien."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import pandas as pd
import pytz
import yfinance as yf

from crash_rebound_config import ALERT_TIMEZONE
from crash_rebound_messages import (
    crash_alert_message,
    rebound_watch_message,
    setup_active_message,
)
from state_utils import get_ticker_state, update_ticker_state


def now_oslo() -> datetime:
    return datetime.now(pytz.timezone(ALERT_TIMEZONE))


def fetch_market_data(symbol: str) -> Dict[str, Any] | None:
    """Hent robuste metrics fra yfinance. Returnerer None ved feil."""
    try:
        ticker = yf.Ticker(symbol)
        daily = ticker.history(period="3mo", interval="1d", auto_adjust=False)
        intraday = ticker.history(period="1d", interval="15m", auto_adjust=False)

        if daily is None or daily.empty:
            print(f"[DATA] Mangler daily data for {symbol}")
            return None

        daily = daily.dropna(how="all")
        if len(daily) < 2:
            print(f"[DATA] For få daily datapunkter for {symbol}")
            return None

        latest_daily = daily.iloc[-1]
        prev_daily = daily.iloc[-2]

        previous_close = float(prev_daily.get("Close", 0.0))
        day_high = float(latest_daily.get("High", 0.0))
        day_low = float(latest_daily.get("Low", 0.0))
        day_volume = float(latest_daily.get("Volume", 0.0))

        last_price = float(latest_daily.get("Close", 0.0))
        if intraday is not None and not intraday.empty:
            intraday = intraday.dropna(how="all")
            if not intraday.empty:
                last_price = float(intraday.iloc[-1].get("Close", last_price))
                day_high = max(day_high, float(intraday["High"].max()))
                day_low = min(day_low, float(intraday["Low"].min()))

        avg_volume = float(daily["Volume"].iloc[-21:-1].mean()) if len(daily) >= 21 else float(daily["Volume"].iloc[:-1].mean())
        avg_volume = avg_volume if pd.notna(avg_volume) and avg_volume > 0 else 0.0
        volume_ratio = (day_volume / avg_volume) if avg_volume > 0 else 0.0

        day_change_pct = ((last_price / previous_close) - 1) * 100 if previous_close > 0 else 0.0
        intraday_drop_pct = ((last_price / day_high) - 1) * 100 if day_high > 0 else 0.0

        metrics = {
            "last_price": last_price,
            "previous_close": previous_close,
            "day_high": day_high,
            "day_low": day_low,
            "day_volume": day_volume,
            "avg_volume": avg_volume,
            "volume_ratio": volume_ratio,
            "day_change_pct": day_change_pct,
            "intraday_drop_pct": intraday_drop_pct,
        }
        print(f"[DATA] Data hentet for {symbol}: close={last_price:.2f}, change={day_change_pct:.2f}%")
        return metrics

    except Exception as exc:
        print(f"[DATA] Feil ved henting for {symbol}: {exc}")
        return None


def _is_crash(meta: dict, m: dict) -> bool:
    hard_day_drop = m["day_change_pct"] <= meta["crash_drop_pct"]
    hard_intraday_drop = m["intraday_drop_pct"] <= meta["intraday_crash_pct"]
    heavy_volume = m["volume_ratio"] >= meta["volume_ratio_min"]
    return (hard_day_drop or hard_intraday_drop) and heavy_volume


def _rebound_watch_ready(m: dict, ticker_state: dict) -> bool:
    panic_low = ticker_state.get("panic_low")
    if panic_low is None or panic_low <= 0:
        return False

    holds_panic_low = m["last_price"] >= panic_low * 1.005
    milder_drop = m["day_change_pct"] > -6.0
    calmer_range = ((m["day_high"] - m["day_low"]) / m["day_low"] * 100) < 8.0 if m["day_low"] > 0 else False
    return holds_panic_low and (milder_drop or calmer_range)


def _setup_ready(meta: dict, m: dict, ticker_state: dict) -> bool:
    panic_low = ticker_state.get("panic_low")
    if panic_low is None or panic_low <= 0:
        return False

    green_day = m["day_change_pct"] >= meta["rebound_confirm_pct"]
    above_panic_with_margin = m["last_price"] >= panic_low * 1.03
    return green_day and above_panic_with_margin


def _calc_rebound_score(metrics: dict, ticker_state: dict) -> int:
    """Enkel defensiv rebound-score (0-10) for WATCH-meldingen."""
    score = 0
    panic_low = ticker_state.get("panic_low")
    panic_high = ticker_state.get("panic_high")

    if panic_low and panic_low > 0 and metrics.get("last_price", 0.0) >= panic_low:
        score += 2

    if metrics.get("day_change_pct", 0.0) > 0:
        score += 2

    if metrics.get("volume_ratio", 0.0) >= 1.2:
        score += 2

    if metrics.get("intraday_drop_pct", 0.0) > -4.0:
        score += 2

    if panic_high and panic_high > panic_low:
        reclaim_ratio = (metrics.get("last_price", 0.0) - panic_low) / (panic_high - panic_low)
        if reclaim_ratio >= 0.35:
            score += 2

    return max(0, min(10, score))


def _calc_risk_label(metrics: dict, ticker_state: dict) -> str:
    """Konservativ risikotagging for rebound-case."""
    panic_low = ticker_state.get("panic_low")
    panic_high = ticker_state.get("panic_high")
    if not panic_low or not panic_high or panic_high <= panic_low:
        return "Høy"

    reclaim_ratio = (metrics.get("last_price", 0.0) - panic_low) / (panic_high - panic_low)
    if reclaim_ratio >= 0.85 and metrics.get("day_change_pct", 0.0) >= 5.0 and metrics.get("volume_ratio", 0.0) >= 2.0:
        return "Lav"
    if reclaim_ratio >= 0.7 and metrics.get("day_change_pct", 0.0) >= 3.0 and metrics.get("volume_ratio", 0.0) >= 1.5:
        return "Middels"
    return "Høy"


def build_trade_plan(last_price: float, panic_low: float) -> Dict[str, float]:
    entry = last_price
    stop = min(last_price * 0.96, panic_low * 0.995)
    target_1 = entry * 1.08
    target_2 = entry * 1.15
    return {
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
    }


def evaluate_ticker(
    symbol: str,
    meta: dict,
    state: Dict[str, Dict[str, Any]],
    can_send_alerts: bool,
    send_message,
) -> Dict[str, Dict[str, Any]]:
    """Evaluer ett symbol og send eventuelle signaler innenfor alert-vindu."""
    metrics = fetch_market_data(symbol)
    if metrics is None:
        return state

    today = now_oslo().date().isoformat()
    ticker_state = get_ticker_state(state, symbol)

    state = update_ticker_state(
        state,
        symbol,
        {
            "last_price": round(metrics["last_price"], 4),
            "last_day_change_pct": round(metrics["day_change_pct"], 4),
        },
    )
    ticker_state = get_ticker_state(state, symbol)

    if _is_crash(meta, metrics):
        crash_updates = {
            "status": "WATCH",
            "crash_date": today,
            "panic_low": round(metrics["day_low"], 4),
            "panic_high": round(metrics["day_high"], 4),
            "last_signal": "CRASH_ALERT",
        }

        should_send = can_send_alerts and ticker_state.get("crash_alert_sent_date") != today
        if should_send:
            msg = crash_alert_message(symbol, meta, metrics)
            if send_message(msg):
                crash_updates["crash_alert_sent_date"] = today
                print(f"[SIGNAL] CRASH ALERT sendt for {symbol}")

        state = update_ticker_state(state, symbol, crash_updates)
        ticker_state = get_ticker_state(state, symbol)

    if ticker_state.get("status") == "WATCH":
        watch_metrics = {
            **metrics,
            "panic_low": ticker_state.get("panic_low"),
            "panic_high": ticker_state.get("panic_high"),
            "rebound_score": _calc_rebound_score(metrics, ticker_state),
            "risk_label": _calc_risk_label(metrics, ticker_state),
            "invalidation_level": ticker_state.get("panic_low"),
        }

        if _rebound_watch_ready(metrics, ticker_state):
            should_send_watch = can_send_alerts and ticker_state.get("rebound_watch_sent_date") != today
            watch_updates = {"last_signal": "REBOUND_WATCH"}
            if should_send_watch:
                msg = rebound_watch_message(symbol, meta, watch_metrics)
                if send_message(msg):
                    watch_updates["rebound_watch_sent_date"] = today
                    print(f"[SIGNAL] REBOUND WATCH sendt for {symbol}")
            state = update_ticker_state(state, symbol, watch_updates)
            ticker_state = get_ticker_state(state, symbol)

        if _setup_ready(meta, metrics, ticker_state):
            should_send_setup = can_send_alerts and ticker_state.get("setup_sent_date") != today
            setup_updates = {"last_signal": "SETUP_AKTIV"}
            if should_send_setup:
                trade_plan = build_trade_plan(metrics["last_price"], ticker_state["panic_low"])
                msg = setup_active_message(symbol, meta, watch_metrics, trade_plan)
                if send_message(msg):
                    setup_updates["setup_sent_date"] = today
                    print(f"[SIGNAL] SETUP AKTIV sendt for {symbol}")
            state = update_ticker_state(state, symbol, setup_updates)

    return state
