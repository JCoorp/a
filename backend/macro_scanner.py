from __future__ import annotations

import numpy as np

from backend.indicators import preparar_indicadores, scalar
from backend.market_data import best_history

MACRO_TICKERS = ["SPY", "QQQ", "FEZ", "EWJ"]


def _score_index(ticker: str) -> float | None:
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


def calcular_macro_score() -> dict[str, float | int | str]:
    scores = [score for ticker in MACRO_TICKERS if (score := _score_index(ticker)) is not None]
    base = float(np.mean(scores)) if scores else 50.0

    vix_penalty = 0.0
    vix_df, _ = best_history("^VIX")
    if vix_df is not None:
        vix = preparar_indicadores(vix_df)
        if not vix.empty:
            last = vix.iloc[-1]
            if scalar(last["Close"]) > scalar(last["EMA20"]):
                vix_penalty += 10
            if scalar(last["RET_5D"]) > 0.08:
                vix_penalty += 15

    macro_score = max(0.0, min(100.0, base - vix_penalty))
    level = 3 if macro_score >= 75 else 2 if macro_score >= 55 else 1 if macro_score >= 35 else 0
    return {
        "score": macro_score,
        "level": level,
        "note": f"Macro técnico basado en {len(scores)} índices; penalización VIX {vix_penalty:.1f}.",
    }
