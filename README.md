# crash-rebound-bot

En Python-basert Telegram-bot for **Crash Rebound**-strategi.

Boten er laget for å overvåke **panikkdrevne fall** i aksjer, og sende tydelige varsler i faser slik at du unngår å kjøpe for tidlig.

## Strategi (3 faser)

1. **⚠️ Crash Alert**
   - Ekstremt fall + høy volumratio registreres.
   - Ticker settes til `WATCH`.
   - Panikkbunn lagres.

2. **👀 Rebound Watch**
   - Når kursen holder seg over panikkbunn og salgspress avtar.
   - Observasjonsfase (ingen kjøpsordre).

3. **🟢 Setup Aktiv**
   - Når case viser tydelig grønn dag + styrke over panikkbunn.
   - Melding inkluderer forslag til inngang, stop, target 1 og target 2.
   - Merkes tydelig som **høy risiko** og **kortsiktig crash-rebound-trade**.

## v1 scope

- Starter med én ticker:
  - `ELO.OL` (Elopak)
- Struktur er laget slik at flere tickere enkelt kan legges til i config.

## Miljøvariabler

Du må sette disse:

- `TOKEN_BOT`
- `CHAT_ID`

> Viktig: Boten bruker disse navnene, ikke gamle alternativer.

## Lokal kjøring

1. Klon repo og gå til mappen.
2. Opprett og aktiver virtuelt miljø.
3. Installer avhengigheter:

```bash
pip install -r requirements.txt
```

4. Sett miljøvariabler:

```bash
export TOKEN_BOT="din_telegram_bot_token"
export CHAT_ID="din_chat_id"
```

5. Start boten:

```bash
python main.py
```

Boten sjekker markedet hvert 15. minutt og sender meldinger kun innenfor alert-vinduet i Oslo-tid (`09:00`–`16:30`).

## Railway deployment

Repoet er klargjort med `Procfile`:

```text
worker: python main.py
```

### Slik setter du miljøvariabler i Railway

1. Gå til prosjektet ditt i Railway.
2. Åpne **Variables**.
3. Legg inn:
   - `TOKEN_BOT`
   - `CHAT_ID`
4. Deploy/redeploy tjenesten.

## Konfigurasjon av watchlist

Watchlist ligger i:

- `crash_rebound_config.py`

Der kan du legge til flere tickere senere uten å endre hovedlogikken i `main.py` eller `crash_rebound.py`.

## Viktig ansvarsfraskrivelse

Dette er en **overvåkningsbot**, ikke en autohandel-bot.
Den plasserer ingen ordre automatisk.
All trading innebærer risiko, spesielt i crash/rebound-scenarier.
