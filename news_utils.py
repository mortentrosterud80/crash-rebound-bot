"""Enkelt og robust nyhets-/sentimentlag for aktive crash/rebound-case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yfinance as yf


NEGATIVE_HINTS = {
    "profit warning": "Resultatvarsel",
    "warning": "Resultatvarsel",
    "guidance cut": "Guidance / outlook",
    "cuts outlook": "Guidance / outlook",
    "lowers outlook": "Guidance / outlook",
    "insider sell": "Innsidesalg / stor eier selger",
    "stake sale": "Innsidesalg / stor eier selger",
    "q": "Regnskap / kvartal",
    "earnings": "Regnskap / kvartal",
    "ceo": "Governance / ledelse",
    "resigns": "Governance / ledelse",
    "contract": "Kontrakt / operasjonelt",
    "order": "Kontrakt / operasjonelt",
    "rates": "Makro / rente / sektor",
    "sector": "Makro / rente / sektor",
}

POSITIVE_WORDS = {
    "beats",
    "rebound",
    "wins",
    "award",
    "growth",
    "raises",
    "improves",
    "strong",
    "positive",
    "upgrade",
}

NEGATIVE_WORDS = {
    "miss",
    "cuts",
    "warning",
    "falls",
    "drop",
    "lawsuit",
    "downgrade",
    "weak",
    "negative",
    "resigns",
    "sell",
}


@dataclass
class SentimentSnapshot:
    sentiment: str
    cause: str
    commentary: str
    source: str
    headlines: list[str]


def _headline_to_cause(text: str) -> str:
    lowered = text.lower()
    for hint, cause in NEGATIVE_HINTS.items():
        if hint in lowered:
            return cause
    return "Uklar årsak"


def _sentiment_bucket(score: int) -> str:
    if score <= -3:
        return "Negativt"
    if score <= -1:
        return "Svakt negativt"
    if score == 0:
        return "Nøytralt"
    if score <= 2:
        return "Bedrende"
    return "Positivt"


def _sentiment_commentary(bucket: str, headlines_found: bool) -> str:
    if not headlines_found:
        return "Ingen tydelige nye signaler hentet nå."
    if bucket == "Negativt":
        return "Negativt nyhetsbilde dominerer fortsatt."
    if bucket == "Svakt negativt":
        return "Fortsatt forsiktig, men mindre panikk enn i går."
    if bucket == "Nøytralt":
        return "Nyhetsbildet virker blandet uten tydelig retning."
    if bucket == "Bedrende":
        return "Nyhetsbildet virker å roe seg."
    return "Mulig bedring i sentiment, men fortsatt usikkerhet."


def _score_headlines(headlines: list[str]) -> int:
    score = 0
    for line in headlines:
        lower = line.lower()
        score += sum(1 for word in POSITIVE_WORDS if word in lower)
        score -= sum(1 for word in NEGATIVE_WORDS if word in lower)
    return score


def _extract_headline_items(news_items: Any) -> list[str]:
    headlines: list[str] = []
    if not isinstance(news_items, list):
        return headlines

    for item in news_items[:6]:
        if isinstance(item, dict):
            title = item.get("title") or item.get("headline")
            if isinstance(title, str) and title.strip():
                headlines.append(title.strip())
    return headlines


def get_sentiment_snapshot(symbol: str) -> SentimentSnapshot:
    """Henter lette headline-signaler via yfinance, med robust fallback."""
    try:
        ticker = yf.Ticker(symbol)
        news_items = getattr(ticker, "news", None)
        if news_items is None and hasattr(ticker, "get_news"):
            try:
                news_items = ticker.get_news()
            except Exception:
                news_items = None

        headlines = _extract_headline_items(news_items)
        if not headlines:
            return SentimentSnapshot(
                sentiment="Nøytralt",
                cause="Uklar årsak",
                commentary="Ingen tydelige nye signaler hentet nå.",
                source="yfinance",
                headlines=[],
            )

        score = _score_headlines(headlines)
        bucket = _sentiment_bucket(score)
        likely_cause = _headline_to_cause(" ".join(headlines[:3]))
        return SentimentSnapshot(
            sentiment=bucket,
            cause=likely_cause,
            commentary=_sentiment_commentary(bucket, headlines_found=True),
            source="yfinance",
            headlines=headlines[:3],
        )

    except Exception:
        return SentimentSnapshot(
            sentiment="Nøytralt",
            cause="Uklar årsak",
            commentary="Nyhetssjekk utilgjengelig akkurat nå.",
            source="fallback",
            headlines=[],
        )
