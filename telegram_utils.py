"""Telegram-hjelpefunksjoner."""

import requests


def send_telegram_message(token_bot: str, chat_id: str, message_html: str) -> bool:
    """Send melding via Telegram Bot API med HTML parse mode."""
    url = f"https://api.telegram.org/bot{token_bot}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("[TELEGRAM] Melding sendt.")
            return True

        print(f"[TELEGRAM] Feil ved sending: HTTP {response.status_code} | {response.text}")
        return False
    except Exception as exc:
        print(f"[TELEGRAM] Unntak ved sending: {exc}")
        return False
