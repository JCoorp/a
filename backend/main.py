from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.ai_analyst import analyze_signal
from backend.config import ROOT_DIR, settings
from backend.database import get_signal, init_db, list_signals, summary, update_ai_summary, update_outcome
from backend.scanner_engine import analizar_activo_en_vivo, escanear_mercado, evaluar_senal
from backend.scheduler import start_scheduler, stop_scheduler
from backend.universe import search_assets, validate_universe_file

app = FastAPI(title="Scanner Global v3.3 Hardened", version=settings.version)
FRONTEND_DIR = ROOT_DIR / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "version": settings.version}


@app.get("/api/status")
def status() -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "ai_provider": settings.ai_provider,
        "openai_model": settings.openai_model if settings.ai_provider == "openai" else None,
        "scan_interval_minutes": settings.scan_interval_minutes,
        "data_sources": {
            "twelve_data": bool(settings.twelve_data_api_key),
            "polygon": bool(settings.polygon_api_key),
            "alpha_vantage": bool(settings.alpha_vantage_api_key),
            "yfinance": settings.enable_yfinance,
        },
        "universe_problems": validate_universe_file(),
        "summary": summary(),
    }


@app.get("/api/signals")
def api_signals(limit: int = 150, level: Optional[int] = None, search: str = "") -> list[dict]:
    return list_signals(limit=limit, level=level, search=search)


@app.post("/api/scan")
def api_scan() -> dict:
    return escanear_mercado()


@app.get("/api/assets/search")
def api_asset_search(q: str = Query(..., min_length=1), limit: int = 20) -> list[dict]:
    return search_assets(q, limit=limit)


@app.post("/api/assets/{ticker}/analyze-now")
def api_analyze_asset_now(ticker: str) -> dict:
    result = analizar_activo_en_vivo(ticker)
    if result is None:
        raise HTTPException(status_code=404, detail="No se pudo analizar el activo o no está en el universo.")
    return result


@app.post("/api/signals/{signal_id}/analyze")
def api_ai_analyze(signal_id: int) -> dict:
    signal = get_signal(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    result = analyze_signal(signal)
    update_ai_summary(signal_id, result)
    signal["ai_summary"] = result
    return {"signal_id": signal_id, "ai_summary": result}


@app.post("/api/signals/{signal_id}/evaluate")
def api_evaluate(signal_id: int) -> dict:
    signal = get_signal(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Señal no encontrada")
    result = evaluar_senal(signal)
    update_outcome(signal_id, result["status"], result["note"])
    return result
