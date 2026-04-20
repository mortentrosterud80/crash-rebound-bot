"""Telegram-hjelpefunksjoner."""

from __future__ import annotations

from dataclasses import dataclass

import requests


def _snippet(value: str, limit: int = 200) -> str:
    compact = " ".join((value or "").split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def _mask_secret(value: str, keep: int = 4) -> str:
    if not value:
        return "<missing>"
    if len(value) <= (keep * 2):
        return "***"
    return f"{value[:keep]}***{value[-keep:]}"


@dataclass
class TelegramSendResult:
    success: bool
    status_code: int | None = None
    response_snippet: str = ""
    error: str | None = None


def send_telegram_message_detailed(
    token_bot: str,
    chat_id: str,
    message_html: str,
    message_type: str = "UNKNOWN",
) -> TelegramSendResult:
    """Send melding via Telegram Bot API og returner detaljert resultat."""
    url = f"https://api.telegram.org/bot{token_bot}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    print(
        "[TELEGRAM] Kaller sendMessage "
        f"type={message_type} token={_mask_secret(token_bot)} chat_id={_mask_secret(chat_id)} "
        f"chars={len(message_html)}"
    )
    try:
        response = requests.post(url, json=payload, timeout=15)
        response_snippet = _snippet(response.text)
        print(f"[TELEGRAM] HTTP {response.status_code} type={message_type} body={response_snippet}")
        if response.status_code == 200:
            print(f"[TELEGRAM] Melding sendt OK for type={message_type}.")
            return TelegramSendResult(success=True, status_code=response.status_code, response_snippet=response_snippet)

        print(f"[TELEGRAM] Feil ved sending for type={message_type}: HTTP {response.status_code}.")
        return TelegramSendResult(success=False, status_code=response.status_code, response_snippet=response_snippet)
    except Exception as exc:
        print(f"[TELEGRAM] Unntak ved sending for type={message_type}: {type(exc).__name__}: {exc}")
        return TelegramSendResult(success=False, error=f"{type(exc).__name__}: {exc}")


def send_telegram_message(token_bot: str, chat_id: str, message_html: str, message_type: str = "UNKNOWN") -> bool:
    """Bakoverkompatibel bool-wrapper rundt Telegram-sending."""
    return send_telegram_message_detailed(
        token_bot=token_bot,
        chat_id=chat_id,
        message_html=message_html,
        message_type=message_type,
    ).success
