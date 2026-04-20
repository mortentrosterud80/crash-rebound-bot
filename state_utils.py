"""Hjelpefunksjoner for state (JSON)."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict

from crash_rebound_config import DEFAULT_TICKER_STATE, STATE_FILE_PATH


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_state() -> Dict[str, Dict[str, Any]]:
    """Last state fra disk, returner tom struktur hvis fil mangler/er tom/ugyldig."""
    _ensure_parent_dir(STATE_FILE_PATH)
    print(f"[STATE] Leser state-fil: {STATE_FILE_PATH}")

    if not os.path.exists(STATE_FILE_PATH):
        print(f"[STATE] Fant ikke state-fil, oppretter: {STATE_FILE_PATH}")
        save_state({})
        return {}

    try:
        with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                print("[STATE] State-fil er tom, bruker tom state.")
                return {}
            data = json.loads(content)
            if not isinstance(data, dict):
                print("[STATE] Ugyldig state-format, bruker tom state.")
                return {}
            print(f"[STATE] Lastet tickere/state-nøkler: {sorted(data.keys())}")
            return data
    except Exception as exc:
        print(f"[STATE] Klarte ikke lese state-fil: {exc}")
        return {}


def save_state(state: Dict[str, Dict[str, Any]]) -> None:
    """Skriv state til disk på en robust måte."""
    _ensure_parent_dir(STATE_FILE_PATH)
    try:
        with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(f"[STATE] Lagret state til {STATE_FILE_PATH} med tickere: {sorted(state.keys())}")
    except Exception as exc:
        print(f"[STATE] Klarte ikke lagre state: {exc}")


def get_ticker_state(state: Dict[str, Dict[str, Any]], ticker: str) -> Dict[str, Any]:
    """Hent ticker-state med defaults."""
    current = state.get(ticker, {})
    merged = deepcopy(DEFAULT_TICKER_STATE)
    merged.update(current)
    return merged


def log_state_blocked_send(ticker: str, reason: str, ticker_state: Dict[str, Any]) -> None:
    """Logg tydelig når state/cooldown blokkerer ny sending."""
    print(
        f"[STATE] Blokkert sending for {ticker}: {reason} | "
        f"phase={ticker_state.get('phase')} "
        f"last_message_type={ticker_state.get('last_message_type')} "
        f"last_message_ts={ticker_state.get('last_message_ts')}"
    )


def update_ticker_state(state: Dict[str, Dict[str, Any]], ticker: str, updates: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Oppdater ticker-state i minnet og returner state."""
    ticker_state = get_ticker_state(state, ticker)
    ticker_state.update(updates)
    ticker_state["updated_at"] = datetime.utcnow().isoformat()
    state[ticker] = ticker_state
    return state
