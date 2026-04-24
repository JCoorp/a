from __future__ import annotations

from typing import Any

from backend.alerts import send_telegram
from backend.config import settings
from backend.consensus_engine import build_consensus
from backend.database import finish_run, insert_signal, start_run, update_outcome
from backend.macro_scanner import calcular_macro_score
from backend.market_data import best_history, collect_news, collect_snapshots
from backend.sector_rotation import calcular_sector_scores, sector_score_for
from backend.stock_scanner import evaluate_asset
from backend.universe import find_asset, load_universe


def _should_include_signal(signal_level: int) -> bool:
    return signal_level >= settings.signal_min_level


def escanear_mercado() -> dict[str, Any]:
    run_id = start_run()
    saved = 0
    total_candidates = 0
    try:
        macro = calcular_macro_score()
        sector_scores = calcular_sector_scores()
        signals = []

        for asset in load_universe():
            history, source = best_history(asset.ticker)
            if history is None or source is None:
                continue
            snapshots = collect_snapshots(asset.ticker)
            consensus = build_consensus(snapshots)
            catalysts = collect_news(asset.ticker)
            sector_score = sector_score_for(asset.sector, sector_scores)
            signal = evaluate_asset(
                asset=asset,
                history=history,
                history_source=source,
                macro_score=float(macro["score"]),
                sector_score=sector_score,
                consensus=consensus,
                catalysts=catalysts,
            )
            if signal is None:
                continue
            total_candidates += 1
            if _should_include_signal(signal.level):
                signals.append(signal)

        signals.sort(key=lambda item: (item.level, item.score_total, item.score_data), reverse=True)
        for signal in signals[: settings.max_signals_per_scan]:
            signal_id = insert_signal(signal, scan_run_id=run_id)
            saved += 1
            if signal.level >= settings.alert_min_level:
                payload = signal.to_dict()
                payload["id"] = signal_id
                send_telegram(payload)

        finish_run(run_id, float(macro["score"]), int(macro["level"]), total_candidates, saved)
        return {
            "status": "finished",
            "run_id": run_id,
            "macro": macro,
            "total_candidates": total_candidates,
            "saved_signals": saved,
        }
    except Exception as exc:
        finish_run(run_id, 0.0, 0, total_candidates, saved, error=str(exc))
        return {"status": "error", "run_id": run_id, "error": str(exc)}


def analizar_activo_en_vivo(ticker: str) -> dict[str, Any] | None:
    asset = find_asset(ticker)
    if asset is None:
        return None
    macro = calcular_macro_score()
    sector_scores = calcular_sector_scores()
    history, source = best_history(asset.ticker)
    if history is None or source is None:
        return None
    consensus = build_consensus(collect_snapshots(asset.ticker))
    catalysts = collect_news(asset.ticker)
    signal = evaluate_asset(
        asset=asset,
        history=history,
        history_source=source,
        macro_score=float(macro["score"]),
        sector_score=sector_score_for(asset.sector, sector_scores),
        consensus=consensus,
        catalysts=catalysts,
    )
    return signal.to_dict() if signal else None


def evaluar_senal(signal: dict[str, Any]) -> dict[str, str]:
    ticker = str(signal["ticker"])
    history, _ = best_history(ticker)
    if history is None or history.empty:
        return {"status": "unknown", "note": "No hay datos suficientes para evaluar la señal."}

    since_price = float(signal["price"])
    stop = float(signal["stop"])
    target = float(signal["target"])
    recent = history.tail(settings.backtest_horizon_days)

    touched_target_at = None
    touched_stop_at = None
    for timestamp, row in recent.iterrows():
        high = float(row["High"])
        low = float(row["Low"])
        if touched_target_at is None and high >= target:
            touched_target_at = str(timestamp)
        if touched_stop_at is None and low <= stop:
            touched_stop_at = str(timestamp)
        if touched_target_at and touched_stop_at:
            break

    if touched_target_at and (not touched_stop_at or touched_target_at <= touched_stop_at):
        status = "target"
        note = f"Tocó objetivo antes que stop. Objetivo: {target:.2f}."
    elif touched_stop_at:
        status = "stop"
        note = f"Tocó stop. Stop: {stop:.2f}."
    else:
        last_close = float(recent.iloc[-1]["Close"])
        change = ((last_close - since_price) / since_price) * 100 if since_price else 0
        status = "active"
        note = f"Sigue activa. Último cierre: {last_close:.2f}; cambio desde señal: {change:.2f}%."

    if "id" in signal:
        update_outcome(int(signal["id"]), status, note)
    return {"status": status, "note": note}
