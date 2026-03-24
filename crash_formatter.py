"""Formattering av Telegram-meldinger for crashbot-faser."""

from __future__ import annotations

from datetime import datetime


def fmt_nok(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}".replace(".", ",") + " %"


def _header(emoji: str, title: str, now_oslo: datetime, day_label: str | None = None) -> str:
    ts = now_oslo.strftime("%H:%M")
    if day_label:
        return f"{emoji} <b>{title}</b> — {day_label} ({ts})"
    return f"{emoji} <b>{title}</b> — {ts}"


def with_test_mode_banner(message_html: str) -> str:
    return f"🧪 <b>TESTMODUS</b>\n{message_html}"


def crash_alert_message(symbol: str, name: str, metrics: dict, now_oslo: datetime, trigger_lines: list[str]) -> str:
    trigger_text = "\n".join([f"• {line}" for line in trigger_lines])
    return (
        f"{_header('⚠️', 'CRASH ALERT', now_oslo)}\n\n"
        f"🧃 <b>{symbol}</b> ({name})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📉 Endring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b> (vs forrige close)\n"
        f"📊 Volum: <b>{metrics.get('volume_ratio', 0.0):.1f}x</b> normal\n\n"
        "Mulig driver:\n"
        f"{trigger_text}\n\n"
        "<b>🧠 AI-vurdering:</b>\n"
        "Dette ligner et event-crash med panikkpreg. Ikke kjøp for tidlig.\n\n"
        "<b>Handling nå:</b>\n"
        "⛔ Ikke kjøp\n"
        "👀 Sett på WATCH\n"
        "⏳ Vent på stabilisering (1–3 dager)"
    )


def rebound_watch_message(symbol: str, name: str, metrics: dict, now_oslo: datetime, day_number: int, observations: list[str]) -> str:
    obs = "\n".join([f"• {line}" for line in observations])
    return (
        f"{_header('👀', 'REBOUND WATCH', now_oslo, f'Dag {day_number}') }\n\n"
        f"🧃 <b>{symbol}</b> ({name})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📉 Endring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b> i dag\n\n"
        "Observasjoner:\n"
        f"{obs}\n\n"
        "<b>AI-signal:</b>\n"
        "Markedet kan være i ferd med å absorbere sjokket.\n"
        "→ Potensiell base-formasjon starter\n\n"
        "Neste steg:\n"
        "🟡 Se etter grønn dag med styrke (> +3 %)\n"
        "🟡 Følg med på nye børsmeldinger / oppdateringer"
    )


def setup_active_message(symbol: str, name: str, metrics: dict, now_oslo: datetime, day_number: int, setup: dict, triggers: list[str]) -> str:
    trigger_text = "\n".join([f"• {line}" for line in triggers])
    return (
        f"{_header('🟢', 'SETUP AKTIV', now_oslo, f'Dag {day_number}') }\n\n"
        f"🧃 <b>{symbol}</b> ({name})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📈 Endring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b>\n\n"
        "Trigger:\n"
        f"{trigger_text}\n\n"
        "🎯 <b>TRADE SETUP — Crash Rebound</b>\n\n"
        f"Inngang: {fmt_nok(setup['entry_low'])} – {fmt_nok(setup['entry_high'])}\n"
        f"Stop: {fmt_nok(setup['stop'])}\n"
        f"Target 1: {fmt_nok(setup['target_1'])}\n"
        f"Target 2: {fmt_nok(setup['target_2'])}\n\n"
        f"R/R: ~1:{setup['rr_to_t1']:.1f}\n\n"
        "⚠️ Risiko\n"
        "• Ny negativ info kan komme\n"
        "• Tillitsskade-case (ikke ren teknisk trade)\n"
        "• Høy volatilitet forventes\n\n"
        "🧠 <b>AI-kommentar</b>\n"
        "Dette er en kortsiktig rebound-trade, ikke en langsiktig investering."
    )


def cool_off_message(symbol: str, name: str, metrics: dict, now_oslo: datetime, reason: str) -> str:
    return (
        f"{_header('🧊', 'COOL OFF', now_oslo)}\n\n"
        f"🧃 <b>{symbol}</b> ({name})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📉 Endring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b>\n\n"
        "<b>AI-vurdering:</b>\n"
        f"{reason}\n\n"
        "👉 Tiltak:\n"
        "COOL OFF"
    )
