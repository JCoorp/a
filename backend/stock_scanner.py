from __future__ import annotations

import math

import pandas as pd

from backend.consensus_engine import Consensus, data_quality_score
from backend.indicators import preparar_indicadores, scalar
from backend.models import Asset, Signal


def _clamp_level(value: int) -> int:
    return max(0, min(3, value))


def evaluate_asset(
    asset: Asset,
    history: pd.DataFrame,
    history_source: str,
    macro_score: float,
    sector_score: float,
    consensus: Consensus,
    catalysts: list[dict],
) -> Signal | None:
    indicators = preparar_indicadores(history)
    if indicators.empty:
        return None

    last = indicators.iloc[-1]
    prev = indicators.iloc[-2]

    close = scalar(last["Close"])
    ema20 = scalar(last["EMA20"])
    ema50 = scalar(last["EMA50"])
    ema20_slope = scalar(last["EMA20_SLOPE"])
    volume = scalar(last["Volume"])
    vol20 = scalar(last["VOL20"])
    high20 = scalar(last["HIGH20"])
    low20 = scalar(last["LOW20"])
    ret5 = scalar(last["RET_5D"])
    ret20 = scalar(last["RET_20D"])
    rsi = scalar(last["RSI14"])
    close_position = scalar(last["CLOSE_POSITION"])

    trend_score = _clamp_level(
        int(close > ema20) + int(ema20 > ema50) + int(ret20 > 0 and ema20_slope > 0)
    )
    volume_score = _clamp_level(int(volume > vol20) + int(volume > vol20 * 1.3) + int(volume > vol20 * 1.8))
    price_score = _clamp_level(
        int(close >= high20 * 0.985) + int(close_position >= 0.60) + int(close >= high20 * 0.997)
    )
    momentum_score = _clamp_level(int(ret5 > 0) + int(ret5 > 0.025) + int(45 <= rsi <= 72))

    support = max(min(low20, ema50), close * 0.90)
    stop = max(support, close * 0.97)
    risk = close - stop
    if risk <= 0:
        stop = close * 0.97
        risk = close - stop
    target = close + risk * 1.6
    rr = (target - close) / risk if risk > 0 else 0
    risk_pct = risk / close if close > 0 else 1
    risk_score = _clamp_level(int(rr >= 1.3) + int(risk_pct <= 0.06) + int(not consensus.blocked))

    score_technical = (
        trend_score * 18
        + volume_score * 12
        + price_score * 15
        + momentum_score * 15
        + risk_score * 15
    ) / 2.25
    score_data = data_quality_score(consensus.quality)
    score_total = (
        score_technical * 0.48
        + macro_score * 0.18
        + sector_score * 0.16
        + score_data * 0.18
    )

    warnings: list[str] = []
    if consensus.blocked:
        warnings.append("Veredicto fuerte bloqueado: fuentes con divergencia excesiva.")
    if consensus.quality == "baja":
        warnings.append("Calidad del dato baja; validar antes de tomar cualquier decisión.")
    if rsi > 72:
        warnings.append("RSI extendido; riesgo de entrada tardía.")
    if close < high20 and high20 > 0 and (high20 - close) / close > 0.03:
        warnings.append("Aún no confirma ruptura de máximo de 20 días.")
    if scalar(prev["Close"]) > scalar(prev["High"]) * 0.98 and close_position < 0.4:
        warnings.append("Cierre débil dentro de la vela; posible pérdida de momentum.")

    if consensus.blocked or consensus.quality == "sin_datos":
        level = 0
        verdict = "Descartar por datos inconsistentes o insuficientes."
    elif score_total >= 78:
        level = 3
        verdict = "Confirmación técnica; revisar como posible operación solo tras validar Kuspit/SIC."
    elif score_total >= 58:
        level = 2
        verdict = "Preparación; candidato interesante, falta confirmación o validación adicional."
    elif score_total >= 38:
        level = 1
        verdict = "Vigilancia; señal temprana, no operable todavía."
    else:
        level = 0
        verdict = "Sin ventaja técnica suficiente."

    if asset.kuspit_status != "yes":
        warnings.append("Disponibilidad Kuspit/SIC no confirmada; validar manualmente antes de operar.")

    if not math.isfinite(score_total):
        return None

    return Signal(
        ticker=asset.ticker,
        name=asset.name,
        region=asset.region,
        sector=asset.sector,
        asset_type=asset.asset_type,
        market=asset.market,
        kuspit_status=asset.kuspit_status,
        thesis_type=asset.thesis_type,
        level=level,
        score_total=round(score_total, 2),
        score_technical=round(score_technical, 2),
        score_macro=round(macro_score, 2),
        score_sector=round(sector_score, 2),
        score_data=round(score_data, 2),
        price=round(float(consensus.median_price or close), 4),
        support=round(support, 4),
        resistance=round(high20, 4),
        stop=round(stop, 4),
        target=round(target, 4),
        rr=round(rr, 2),
        trend_score=trend_score,
        volume_score=volume_score,
        price_score=price_score,
        momentum_score=momentum_score,
        risk_score=risk_score,
        rsi=round(rsi, 2),
        ret5=round(ret5 * 100, 2),
        ret20=round(ret20 * 100, 2),
        data_quality=consensus.quality,
        consensus_label=consensus.label,
        source_count=consensus.total_sources,
        source_valid_count=consensus.valid_sources,
        source_divergence_pct=consensus.divergence_pct,
        data_sources=consensus.snapshots,
        warnings=warnings,
        catalysts=catalysts,
        verdict=verdict,
    )
