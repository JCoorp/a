from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    version: str = "3.3.0-hardened"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    data_dir: Path = Path(os.getenv("DATA_DIR", str(ROOT_DIR / "data")))
    db_path: Path = Path(os.getenv("DB_PATH", str(ROOT_DIR / "data" / "scanner_global.db")))
    universe_path: Path = Path(os.getenv("UNIVERSE_PATH", str(ROOT_DIR / "data" / "universe_global.csv")))
    kuspit_list_path: Path = Path(os.getenv("KUSPIT_LIST_PATH", str(ROOT_DIR / "data" / "kuspit_watchlist.csv")))

    scan_interval_minutes: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))
    run_scan_on_startup: bool = _bool_env("RUN_SCAN_ON_STARTUP", True)
    signal_min_level: int = int(os.getenv("SIGNAL_MIN_LEVEL", "1"))
    alert_min_level: int = int(os.getenv("ALERT_MIN_LEVEL", "3"))
    max_signals_per_scan: int = int(os.getenv("MAX_SIGNALS_PER_SCAN", "30"))
    min_data_rows: int = int(os.getenv("MIN_DATA_ROWS", "80"))

    data_period: str = os.getenv("PERIODO_DATOS", "6mo")
    data_interval: str = os.getenv("INTERVALO_DATOS", "1d")
    kuspit_filter_mode: str = os.getenv("KUSPIT_FILTER_MODE", "tag").lower().strip()

    twelve_data_api_key: str = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    polygon_api_key: str = os.getenv("POLYGON_API_KEY", "").strip()
    alpha_vantage_api_key: str = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    enable_yfinance: bool = _bool_env("ENABLE_YFINANCE", True)

    consensus_high_min_sources: int = int(os.getenv("CONSENSUS_HIGH_MIN_SOURCES", "3"))
    consensus_medium_min_sources: int = int(os.getenv("CONSENSUS_MEDIUM_MIN_SOURCES", "2"))
    consensus_high_max_divergence_pct: float = float(os.getenv("CONSENSUS_HIGH_MAX_DIVERGENCE_PCT", "0.35"))
    consensus_medium_max_divergence_pct: float = float(os.getenv("CONSENSUS_MEDIUM_MAX_DIVERGENCE_PCT", "0.85"))
    consensus_block_max_divergence_pct: float = float(os.getenv("CONSENSUS_BLOCK_MAX_DIVERGENCE_PCT", "1.50"))

    ai_provider: str = os.getenv("AI_PROVIDER", "heuristic").lower().strip()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/responses").strip()
    openai_timeout_seconds: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    backtest_horizon_days: int = int(os.getenv("BACKTEST_HORIZON_DAYS", "20"))
    duplicate_signal_window_hours: int = int(os.getenv("DUPLICATE_SIGNAL_WINDOW_HOURS", "12"))


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
