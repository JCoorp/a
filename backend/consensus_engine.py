from __future__ import annotations

from statistics import median

from backend.config import settings
from backend.models import Consensus, Snapshot


def _price_divergence_pct(prices: list[float]) -> float | None:
    if len(prices) < 2:
        return None
    median_price = median(prices)
    if median_price <= 0:
        return None
    return ((max(prices) - min(prices)) / median_price) * 100


def data_quality_score(quality: str) -> float:
    return {"alta": 100.0, "media": 70.0, "baja": 35.0, "sin_datos": 0.0}.get(quality, 0.0)


def build_consensus(snapshots: list[Snapshot]) -> Consensus:
    valid = [snap for snap in snapshots if snap.ok and snap.price is not None and snap.price > 0]
    prices = [float(snap.price) for snap in valid]
    divergence = _price_divergence_pct(prices)
    median_price = median(prices) if prices else None

    if not valid:
        return Consensus(
            quality="sin_datos",
            label="0/0 fuentes válidas",
            valid_sources=0,
            total_sources=len(snapshots),
            divergence_pct=None,
            median_price=None,
            blocked=True,
            reason="Ninguna fuente devolvió precio válido.",
            snapshots=[snap.to_dict() for snap in snapshots],
        )

    blocked = bool(divergence is not None and divergence > settings.consensus_block_max_divergence_pct)

    if blocked:
        quality = "baja"
        reason = (
            f"Fuentes con divergencia {divergence:.2f}%, por encima del límite "
            f"{settings.consensus_block_max_divergence_pct:.2f}%."
        )
    elif (
        len(valid) >= settings.consensus_high_min_sources
        and divergence is not None
        and divergence <= settings.consensus_high_max_divergence_pct
    ):
        quality = "alta"
        reason = "Múltiples fuentes coinciden con baja divergencia."
    elif (
        len(valid) >= settings.consensus_medium_min_sources
        and (divergence is None or divergence <= settings.consensus_medium_max_divergence_pct)
    ):
        quality = "media"
        reason = "Consenso aceptable, aunque no institucional."
    else:
        quality = "baja"
        reason = "Pocas fuentes válidas o consenso insuficiente."

    label = f"{len(valid)}/{len(snapshots)} fuentes válidas"
    if divergence is not None:
        label += f" · divergencia {divergence:.2f}%"

    return Consensus(
        quality=quality,
        label=label,
        valid_sources=len(valid),
        total_sources=len(snapshots),
        divergence_pct=divergence,
        median_price=median_price,
        blocked=blocked,
        reason=reason,
        snapshots=[snap.to_dict() for snap in snapshots],
    )
