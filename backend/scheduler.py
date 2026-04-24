from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.scanner_engine import escanear_mercado

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        escanear_mercado,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="market_scan",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    if settings.run_scan_on_startup:
        escanear_mercado()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
