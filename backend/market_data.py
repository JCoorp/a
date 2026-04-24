from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from backend.config import settings
from backend.indicators import REQUIRED_OHLCV_COLUMNS
from backend.models import Snapshot


class MarketDataProvider:
    name = "base"

    def enabled(self) -> bool:
        return False

    def history(self, ticker: str) -> pd.DataFrame | None:
        return None

    def snapshot(self, ticker: str) -> Snapshot:
        return Snapshot(self.name, ticker, None, None, None, None, False, "no implementado")

    def news(self, ticker: str) -> list[dict[str, Any]]:
        return []


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.get_level_values(0):
            df.columns = df.columns.get_level_values(0)
        elif "Close" in df.columns.get_level_values(1):
            df.columns = df.columns.get_level_values(1)
    if any(col not in df.columns for col in REQUIRED_OHLCV_COLUMNS):
        return None
    clean = df[REQUIRED_OHLCV_COLUMNS].copy().dropna()
    return clean if len(clean) >= settings.min_data_rows else None


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    def enabled(self) -> bool:
        return settings.enable_yfinance

    def history(self, ticker: str) -> pd.DataFrame | None:
        if not self.enabled():
            return None
        try:
            df = yf.download(
                ticker,
                period=settings.data_period,
                interval=settings.data_interval,
                progress=False,
                auto_adjust=True,
                group_by="column",
            )
            return _normalize_ohlcv(df)
        except Exception:
            return None

    def snapshot(self, ticker: str) -> Snapshot:
        try:
            df = yf.download(
                ticker,
                period="5d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="column",
            )
            clean = _normalize_ohlcv(df)
            if clean is None or clean.empty:
                return Snapshot(self.name, ticker, None, None, None, None, False, "sin datos")
            last = clean.iloc[-1]
            return Snapshot(
                source=self.name,
                ticker=ticker,
                price=float(last["Close"]),
                volume=float(last["Volume"]),
                currency=None,
                timestamp=str(clean.index[-1]),
                ok=True,
            )
        except Exception as exc:
            return Snapshot(self.name, ticker, None, None, None, None, False, str(exc))

    def news(self, ticker: str) -> list[dict[str, Any]]:
        try:
            items = yf.Ticker(ticker).news or []
        except Exception:
            return []
        output: list[dict[str, Any]] = []
        for item in items[:5]:
            output.append(
                {
                    "source": "yfinance",
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published_at": item.get("providerPublishTime"),
                }
            )
        return output


class TwelveDataProvider(MarketDataProvider):
    name = "twelve_data"

    def enabled(self) -> bool:
        return bool(settings.twelve_data_api_key)

    def history(self, ticker: str) -> pd.DataFrame | None:
        if not self.enabled() or settings.data_interval != "1d":
            return None
        try:
            response = requests.get(
                "https://api.twelvedata.com/time_series",
                params={
                    "symbol": ticker,
                    "interval": "1day",
                    "outputsize": 220,
                    "apikey": settings.twelve_data_api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if "values" not in payload:
                return None
            rows = []
            for value in payload["values"]:
                rows.append(
                    {
                        "Date": pd.to_datetime(value["datetime"]),
                        "Open": float(value["open"]),
                        "High": float(value["high"]),
                        "Low": float(value["low"]),
                        "Close": float(value["close"]),
                        "Volume": float(value.get("volume") or 0),
                    }
                )
            df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
            return _normalize_ohlcv(df)
        except Exception:
            return None

    def snapshot(self, ticker: str) -> Snapshot:
        if not self.enabled():
            return Snapshot(self.name, ticker, None, None, None, None, False, "sin API key")
        try:
            response = requests.get(
                "https://api.twelvedata.com/quote",
                params={"symbol": ticker, "apikey": settings.twelve_data_api_key},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") == "error":
                return Snapshot(self.name, ticker, None, None, None, None, False, payload.get("message"))
            price = payload.get("close") or payload.get("price")
            return Snapshot(
                self.name,
                ticker,
                float(price) if price not in {None, ""} else None,
                float(payload.get("volume") or 0),
                payload.get("currency"),
                payload.get("datetime") or dt.datetime.utcnow().isoformat(),
                price not in {None, ""},
                None,
            )
        except Exception as exc:
            return Snapshot(self.name, ticker, None, None, None, None, False, str(exc))


class PolygonProvider(MarketDataProvider):
    name = "polygon"

    def enabled(self) -> bool:
        return bool(settings.polygon_api_key)

    def _can_query(self, ticker: str) -> bool:
        return self.enabled() and "." not in ticker

    def history(self, ticker: str) -> pd.DataFrame | None:
        if not self._can_query(ticker):
            return None
        try:
            end = dt.date.today()
            start = end - dt.timedelta(days=260)
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
            response = requests.get(
                url,
                params={"adjusted": "true", "sort": "asc", "limit": 5000, "apiKey": settings.polygon_api_key},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("results"):
                return None
            rows = []
            for item in payload["results"]:
                rows.append(
                    {
                        "Date": pd.to_datetime(item["t"], unit="ms"),
                        "Open": float(item["o"]),
                        "High": float(item["h"]),
                        "Low": float(item["l"]),
                        "Close": float(item["c"]),
                        "Volume": float(item.get("v") or 0),
                    }
                )
            df = pd.DataFrame(rows).set_index("Date")
            return _normalize_ohlcv(df)
        except Exception:
            return None

    def snapshot(self, ticker: str) -> Snapshot:
        if not self._can_query(ticker):
            return Snapshot(self.name, ticker, None, None, None, None, False, "no aplicable o sin API key")
        try:
            response = requests.get(
                f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev",
                params={"adjusted": "true", "apiKey": settings.polygon_api_key},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []
            if not results:
                return Snapshot(self.name, ticker, None, None, None, None, False, "sin resultados")
            item = results[0]
            return Snapshot(
                self.name,
                ticker,
                float(item["c"]),
                float(item.get("v") or 0),
                "USD",
                str(pd.to_datetime(item["t"], unit="ms")),
                True,
            )
        except Exception as exc:
            return Snapshot(self.name, ticker, None, None, None, None, False, str(exc))


class AlphaVantageProvider(MarketDataProvider):
    name = "alpha_vantage"

    def enabled(self) -> bool:
        return bool(settings.alpha_vantage_api_key)

    def history(self, ticker: str) -> pd.DataFrame | None:
        if not self.enabled():
            return None
        try:
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "TIME_SERIES_DAILY_ADJUSTED",
                    "symbol": ticker,
                    "apikey": settings.alpha_vantage_api_key,
                    "outputsize": "compact",
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            series = payload.get("Time Series (Daily)")
            if not series:
                return None
            rows = []
            for date, item in series.items():
                rows.append(
                    {
                        "Date": pd.to_datetime(date),
                        "Open": float(item["1. open"]),
                        "High": float(item["2. high"]),
                        "Low": float(item["3. low"]),
                        "Close": float(item["5. adjusted close"]),
                        "Volume": float(item.get("6. volume") or 0),
                    }
                )
            df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
            return _normalize_ohlcv(df)
        except Exception:
            return None

    def snapshot(self, ticker: str) -> Snapshot:
        hist = self.history(ticker)
        if hist is None or hist.empty:
            return Snapshot(self.name, ticker, None, None, None, None, False, "sin datos")
        last = hist.iloc[-1]
        return Snapshot(
            self.name,
            ticker,
            float(last["Close"]),
            float(last["Volume"]),
            "USD",
            str(hist.index[-1]),
            True,
        )

    def news(self, ticker: str) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        try:
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": settings.alpha_vantage_api_key},
                timeout=20,
            )
            response.raise_for_status()
            feed = response.json().get("feed") or []
            return [
                {
                    "source": "alpha_vantage",
                    "title": item.get("title", ""),
                    "publisher": item.get("source", ""),
                    "link": item.get("url", ""),
                    "published_at": item.get("time_published"),
                    "sentiment": item.get("overall_sentiment_label"),
                }
                for item in feed[:5]
            ]
        except Exception:
            return []


PROVIDERS: list[MarketDataProvider] = [
    TwelveDataProvider(),
    PolygonProvider(),
    AlphaVantageProvider(),
    YFinanceProvider(),
]


def enabled_providers() -> list[MarketDataProvider]:
    return [provider for provider in PROVIDERS if provider.enabled()]


def best_history(ticker: str) -> tuple[pd.DataFrame | None, str | None]:
    for provider in enabled_providers():
        history = provider.history(ticker)
        if history is not None and not history.empty:
            return history, provider.name
    return None, None


def collect_snapshots(ticker: str) -> list[Snapshot]:
    return [provider.snapshot(ticker) for provider in enabled_providers()]


def collect_news(ticker: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for provider in enabled_providers():
        for item in provider.news(ticker):
            title = str(item.get("title", "")).strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                items.append(item)
            if len(items) >= 8:
                return items
    return items
