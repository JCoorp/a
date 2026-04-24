from __future__ import annotations

from typing import Any

import pandas as pd

REQUIRED_OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def scalar(value: Any) -> float:
    """Return a plain float from pandas, numpy or scalar values."""
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except Exception:
            pass
    if hasattr(value, "iloc"):
        return float(value.iloc[0])
    return float(value)


def validate_ohlcv(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_OHLCV_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas OHLCV requeridas: {', '.join(missing)}")


def preparar_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators used by the scanner."""
    validate_ohlcv(df)
    clean = df[REQUIRED_OHLCV_COLUMNS].copy().dropna()

    clean["EMA20"] = clean["Close"].ewm(span=20, adjust=False).mean()
    clean["EMA50"] = clean["Close"].ewm(span=50, adjust=False).mean()
    clean["EMA20_SLOPE"] = clean["EMA20"].diff(5)
    clean["VOL20"] = clean["Volume"].rolling(20).mean()
    clean["RET_5D"] = clean["Close"].pct_change(5)
    clean["RET_20D"] = clean["Close"].pct_change(20)
    clean["HIGH20"] = clean["High"].rolling(20).max()
    clean["LOW20"] = clean["Low"].rolling(20).min()

    delta = clean["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    relative_strength = gain / loss.replace(0, pd.NA)
    clean["RSI14"] = 100 - (100 / (1 + relative_strength))
    clean["RSI14"] = clean["RSI14"].fillna(50)

    candle_range = (clean["High"] - clean["Low"]).replace(0, pd.NA)
    clean["CLOSE_POSITION"] = ((clean["Close"] - clean["Low"]) / candle_range).fillna(0.5)

    return clean.dropna()
