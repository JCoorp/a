from __future__ import annotations

import numpy as np

from backend.indicators import preparar_indicadores, scalar
from backend.market_data import best_history

SECTOR_ETFS = {
    "Technology": "XLK",
    "Semiconductors": "SMH",
    "Financials": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Broad Market": "SPY",
}


def _score_sector_etf(ticker: str) -> float | None:
    df, _ = best_history(ticker)
    if df is None:
        return None
    indicators = preparar_indicadores(df)
    if indicators.empty:
        return None
    last = indicators.iloc[-1]
    score = 0.0
    if scalar(last["Close"]) > scalar(last["EMA20"]):
        score += 25
    if scalar(last["EMA20"]) > scalar(last["EMA50"]):
        score += 25
    if scalar(last["RET_5D"]) > 0:
        score += 20
    if scalar(last["RET_20D"]) > 0:
        score += 20
    if scalar(last["Volume"]) > scalar(last["VOL20"]):
        score += 10
    return score


def calcular_sector_scores() -> dict[str, float]:
    scores: dict[str, float] = {}
    for sector, ticker in SECTOR_ETFS.items():
        score = _score_sector_etf(ticker)
        if score is not None:
            scores[sector] = float(score)
    return scores


def sector_score_for(sector: str, sector_scores: dict[str, float]) -> float:
    if sector in sector_scores:
        return sector_scores[sector]
    if not sector_scores:
        return 50.0
    return float(np.mean(list(sector_scores.values())))
