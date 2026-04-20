"""Telegram-hjelpefunksjoner."""

from __future__ import annotations

import requests


def _snippet(value: str, limit: int = 200) -> str:
    compact = " ".join((value or "").split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def send_telegram_message(token_bot: str, chat_id: str, message_html: str, message_type: str = "UNKNOWN") -> bool:
    """Send melding via Telegram Bot API med HTML parse mode."""
    url = f"https://api.telegram.org/bot{token_bot}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    print(f"[TELEGRAM] Kaller sendMessage for type={message_type} (chars={len(message_html)})")
    try:
        response = requests.post(url, json=payload, timeout=15)
        response_snippet = _snippet(response.text)
        print(f"[TELEGRAM] HTTP {response.status_code} for type={message_type} | body={response_snippet}")
        if response.status_code == 200:
            print(f"[TELEGRAM] Melding sendt for type={message_type}.")
            return True

        print(f"[TELEGRAM] Feil ved sending for type={message_type}: HTTP {response.status_code}")
        return False
    except Exception as exc:
        print(f"[TELEGRAM] Unntak ved sending for type={message_type}: {exc}")
        return False
