from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    region: str
    sector: str
    asset_type: str
    market: str
    kuspit_status: str
    thesis_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Snapshot:
    source: str
    ticker: str
    price: float | None
    volume: float | None
    currency: str | None
    timestamp: str | None
    ok: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Consensus:
    quality: str
    label: str
    valid_sources: int
    total_sources: int
    divergence_pct: float | None
    median_price: float | None
    blocked: bool
    reason: str
    snapshots: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Signal:
    ticker: str
    name: str
    region: str
    sector: str
    asset_type: str
    market: str
    kuspit_status: str
    thesis_type: str
    level: int
    score_total: float
    score_technical: float
    score_macro: float
    score_sector: float
    score_data: float
    price: float
    support: float
    resistance: float
    stop: float
    target: float
    rr: float
    trend_score: int
    volume_score: int
    price_score: int
    momentum_score: int
    risk_score: int
    rsi: float
    ret5: float
    ret20: float
    data_quality: str
    consensus_label: str
    source_count: int
    source_valid_count: int
    source_divergence_pct: float | None
    data_sources: list[dict[str, Any]]
    warnings: list[str]
    catalysts: list[dict[str, Any]]
    verdict: str
    ai_summary: str = "IA pendiente. Selecciona esta señal y presiona 'Analizar con IA'."
    outcome_status: str = "pending"
    outcome_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
