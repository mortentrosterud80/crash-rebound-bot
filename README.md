# crash-rebound-bot

Crash Rebound-bot for Telegram, først lansert for **ELO.OL**.

## Første versjon (v1)

Denne boten er en **advisory bot** (ikke auto-trading) med fire faser:

1. `CRASH_ALERT`
2. `REBOUND_WATCH`
3. `SETUP_ACTIVE`
4. `COOL_OFF`

Målet er å bremse panikk-kjøp, vente på stabilisering, og kun sende konkret setup når edge faktisk er der.

## Filstruktur (crash-modul)

- `crash_runner.py` – hovedloop, tidsvindu, Telegram-send
- `crash_detector.py` – datahenting + state-maskin + faseoverganger
- `crash_formatter.py` – Telegram-meldingsformat
- `data/crash_state.json` – persist state mellom kjøringer

## Miljøvariabler

- `TOKEN_BOT`
- `CHAT_ID`

## Kjøring

```bash
pip install -r requirements.txt
python main.py
```

Boten kjører hvert 15. minutt og sender varsler i Oslo-børsens åpningstid.
