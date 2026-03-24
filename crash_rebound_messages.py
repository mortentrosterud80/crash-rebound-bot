"""Formattering av Telegram-meldinger for Crash Rebound."""

from __future__ import annotations


def fmt_nok(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: float | None, decimals: int = 1, signed: bool = True) -> str:
    if value is None:
        return "-"
    sign = "+" if signed and value > 0 else ""
    txt = f"{sign}{value:.{decimals}f}".replace(".", ",")
    return f"{txt} %"


def crash_alert_message(symbol: str, meta: dict, metrics: dict) -> str:
    return (
        "⚠️ <b>CRASH ALERT</b>\n\n"
        f"{meta['emoji']} <b>{symbol}</b> ({meta['name']})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📉 Endring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b> (vs forrige close)\n"
        f"📊 Volum: <b>{fmt_nok(metrics.get('volume_ratio'))}x</b> normal\n"
        f"🩸 Panikkbunn: <b>{fmt_nok(metrics.get('day_low'))} NOK</b>\n\n"
        "Status: <b>WATCH</b>\n\n"
        "<b>AI-vurdering:</b>\n"
        "Panikkdrevet fall registrert. Dette kan være et event/crash-case.\n"
        "Ikke fang kniven nå — vent på stabilisering.\n\n"
        "<b>Handling nå:</b>\n"
        "⛔ Ikke kjøp\n"
        "👀 Overvåk\n"
        "⏳ Vent 1–3 dager"
    )


def rebound_watch_message(symbol: str, meta: dict, metrics: dict) -> str:
    return (
        "👀 <b>REBOUND WATCH</b>\n\n"
        f"{meta['emoji']} <b>{symbol}</b> ({meta['name']})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📉 Dagsendring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b>\n"
        f"🩸 Panikkbunn: <b>{fmt_nok(metrics.get('panic_low'))} NOK</b>\n"
        f"📊 Volum: <b>{fmt_nok(metrics.get('volume_ratio'))}x</b> normal\n\n"
        "Status: <b>WATCH</b>\n\n"
        "<b>AI-vurdering:</b>\n"
        "Kursen holder over panikkbunn og salgspresset ser ut til å roe seg.\n"
        "Case kan være på vei inn i stabilisering/base.\n\n"
        "<b>Handling nå:</b>\n"
        "⏳ Ingen kjøpsordre ennå\n"
        "👀 Følg videre pris/volum tett"
    )


def setup_active_message(symbol: str, meta: dict, metrics: dict, trade_plan: dict) -> str:
    return (
        "🟢 <b>SETUP AKTIV</b>\n\n"
        f"{meta['emoji']} <b>{symbol}</b> ({meta['name']})\n"
        f"💰 Kurs: <b>{fmt_nok(metrics.get('last_price'))} NOK</b>\n"
        f"📈 Dagsendring: <b>{fmt_pct(metrics.get('day_change_pct'))}</b>\n"
        f"🩸 Panikkbunn: <b>{fmt_nok(metrics.get('panic_low'))} NOK</b>\n\n"
        "<b>Crash Rebound-plan (kortsiktig):</b>\n"
        f"➡️ Inngang: <b>{fmt_nok(trade_plan['entry'])} NOK</b>\n"
        f"🛑 Stop: <b>{fmt_nok(trade_plan['stop'])} NOK</b>\n"
        f"🎯 Target 1: <b>{fmt_nok(trade_plan['target_1'])} NOK</b>\n"
        f"🚀 Target 2: <b>{fmt_nok(trade_plan['target_2'])} NOK</b>\n\n"
        "<b>Risiko:</b> Høy\n"
        "<b>Type:</b> Crash Rebound\n\n"
        "<b>AI-vurdering:</b>\n"
        "Panikkfasen ser ut til å avta, og et mulig rebound-setup tar form.\n"
        "Dette er <b>ikke</b> et langsiktig kjøpssignal."
    )
