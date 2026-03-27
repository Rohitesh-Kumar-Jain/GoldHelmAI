from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from app.utils.config import get_settings


logger = logging.getLogger(__name__)


class DataUnavailableError(RuntimeError):
    """Raised when no valid market data can be loaded."""


class GoldDataService:
    """Fetches and caches historical gold futures data."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ticker = settings.gold_ticker
        self.lookback_days = settings.data_lookback_days
        self.cache_ttl_seconds = settings.data_cache_ttl_seconds
        self.cache_path = Path(__file__).resolve().parents[2] / "data" / "gold_prices.csv"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._in_memory_cache: pd.DataFrame | None = None
        self._cache_loaded_at: datetime | None = None

    def fetch_price_history(self) -> pd.DataFrame:
        if self._is_memory_cache_fresh():
            return self._in_memory_cache.copy()

        try:
            raw = yf.download(
                self.ticker,
                period=f"{self.lookback_days}d",
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if raw.empty:
                raise DataUnavailableError("yfinance returned an empty dataset.")

            frame = self._normalize_history_frame(raw.reset_index())
            self._persist_cache(frame)
            logger.info("Fetched %s rows of market data for %s.", len(frame), self.ticker)
            return frame.copy()
        except Exception as exc:
            logger.warning("Falling back to cached data for %s: %s", self.ticker, exc)
            cached = self._load_cached_history()
            if cached.empty:
                raise DataUnavailableError(
                    "Unable to fetch gold price data and no valid cache is available."
                ) from exc
            return cached

    def _load_cached_history(self) -> pd.DataFrame:
        if not self.cache_path.exists():
            raise DataUnavailableError("No local data cache is available.")

        frame = pd.read_csv(self.cache_path)
        normalized = self._normalize_history_frame(frame)
        self._update_memory_cache(normalized)
        return normalized.copy()

    def get_price_history(self) -> list[dict[str, Any]]:
        frame = self.fetch_price_history()
        return [
            {"date": row["date"], "close": round(float(row["close"]), 2)}
            for _, row in frame.iterrows()
        ]

    def get_latest_price(self) -> dict[str, Any]:
        frame = self.fetch_price_history()
        latest = frame.iloc[-1]
        return {
            "ticker": self.ticker,
            "date": latest["date"],
            "price": round(float(latest["close"]), 2),
        }

    def get_training_frame(self) -> pd.DataFrame:
        return self.fetch_price_history().copy()

    def _normalize_history_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        if isinstance(normalized.columns, pd.MultiIndex):
            normalized.columns = [
                col[0] if isinstance(col, tuple) else col for col in normalized.columns
            ]

        rename_map = {"Date": "date", "Close": "close"}
        normalized = normalized.rename(columns=rename_map)

        if "date" not in normalized.columns or "close" not in normalized.columns:
            raise DataUnavailableError("Expected date and close columns were not present.")

        normalized = normalized[["date", "close"]].copy()
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
        normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce")
        normalized = normalized.dropna(subset=["date", "close"])
        normalized = normalized.drop_duplicates(subset=["date"]).sort_values("date")

        if normalized.empty:
            raise DataUnavailableError("No valid market rows remained after normalization.")

        normalized["date"] = normalized["date"].astype(str)
        normalized = normalized.reset_index(drop=True)
        return normalized

    def _persist_cache(self, frame: pd.DataFrame) -> None:
        frame.to_csv(self.cache_path, index=False)
        self._update_memory_cache(frame)

    def _update_memory_cache(self, frame: pd.DataFrame) -> None:
        self._in_memory_cache = frame.copy()
        self._cache_loaded_at = datetime.now(UTC)

    def _is_memory_cache_fresh(self) -> bool:
        if self._in_memory_cache is None or self._cache_loaded_at is None:
            return False

        age_seconds = (datetime.now(UTC) - self._cache_loaded_at).total_seconds()
        return age_seconds < self.cache_ttl_seconds
