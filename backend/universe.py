from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import pandas as pd

from backend.config import settings
from backend.models import Asset

REQUIRED_COLUMNS = [
    "ticker",
    "name",
    "region",
    "sector",
    "asset_type",
    "market",
    "kuspit_status",
    "thesis_type",
]


def validate_universe_file(path: Path = settings.universe_path) -> list[str]:
    """Validate CSV structure and return human-readable problems."""
    problems: list[str] = []
    if not path.exists():
        return [f"No existe el archivo de universo: {path}"]

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return ["El archivo de universo está vacío."]

        missing = [col for col in REQUIRED_COLUMNS if col not in header]
        if missing:
            problems.append(f"Faltan columnas: {', '.join(missing)}")

        expected_len = len(header)
        for idx, row in enumerate(reader, start=2):
            if len(row) != expected_len:
                problems.append(
                    f"Línea {idx}: se esperaban {expected_len} columnas y llegaron {len(row)}."
                )

    return problems


def load_universe(path: Path = settings.universe_path) -> list[Asset]:
    problems = validate_universe_file(path)
    if problems:
        raise ValueError("Universo inválido: " + " | ".join(problems))

    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    assets: list[Asset] = []
    seen: set[str] = set()

    for _, row in df.iterrows():
        ticker = row["ticker"].strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        assets.append(
            Asset(
                ticker=ticker,
                name=row["name"].strip(),
                region=row["region"].strip(),
                sector=row["sector"].strip(),
                asset_type=row["asset_type"].strip(),
                market=row["market"].strip(),
                kuspit_status=row["kuspit_status"].strip().lower(),
                thesis_type=row["thesis_type"].strip(),
            )
        )

    return assets


def search_assets(query: str, limit: int = 20, assets: Iterable[Asset] | None = None) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []

    source_assets = list(assets) if assets is not None else load_universe()
    matches: list[dict] = []

    for asset in source_assets:
        haystack = " ".join(
            [
                asset.ticker,
                asset.name,
                asset.region,
                asset.sector,
                asset.asset_type,
                asset.market,
                asset.thesis_type,
            ]
        ).lower()
        if q in haystack:
            matches.append(asset.to_dict())
        if len(matches) >= limit:
            break

    return matches


def find_asset(ticker: str) -> Asset | None:
    normalized = ticker.strip().upper()
    for asset in load_universe():
        if asset.ticker == normalized:
            return asset
    return None
