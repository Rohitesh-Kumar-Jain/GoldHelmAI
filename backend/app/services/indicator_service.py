from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class IndicatorService:
    """Computes technical indicators, summary counts, and chart-ready series."""

    def compute_indicators(self, frame: pd.DataFrame) -> dict[str, Any]:
        market = frame.copy()
        market["close"] = pd.to_numeric(market["close"], errors="coerce")
        market["high"] = pd.to_numeric(market.get("high", market["close"]), errors="coerce")
        market["low"] = pd.to_numeric(market.get("low", market["close"]), errors="coerce")
        market["volume"] = pd.to_numeric(market.get("volume", 0.0), errors="coerce").fillna(0.0)
        market = market.dropna(subset=["close", "high", "low"]).reset_index(drop=True)

        if market.empty:
            return {
                "technical_indicators": {},
                "indicator_summary": {"bullish": 0, "bearish": 0, "neutral": 0},
                "indicator_charts": {},
            }

        rsi = self._rsi(market)
        moving_averages = self._moving_averages(market)
        macd = self._macd(market)
        bollinger_bands = self._bollinger_bands(market)
        momentum = self._momentum(market)
        atr = self._atr(market)
        stochastic = self._stochastic(market)
        obv = self._obv(market)
        fibonacci = self._fibonacci(market)
        adx = self._adx(market)

        indicators = {
            "rsi": rsi["latest"],
            "moving_averages": moving_averages["latest"],
            "macd": macd["latest"],
            "bollinger_bands": bollinger_bands["latest"],
            "momentum": momentum["latest"],
            "atr": atr["latest"],
            "stochastic": stochastic["latest"],
            "obv": obv["latest"],
            "fibonacci": fibonacci["latest"],
            "adx": adx["latest"],
        }
        charts = {
            "rsi": rsi["chart"],
            "moving_averages": moving_averages["chart"],
            "macd": macd["chart"],
            "bollinger_bands": bollinger_bands["chart"],
            "momentum": momentum["chart"],
            "atr": atr["chart"],
            "stochastic": stochastic["chart"],
            "obv": obv["chart"],
            "fibonacci": fibonacci["chart"],
            "adx": adx["chart"],
        }

        summary = {"bullish": 0, "bearish": 0, "neutral": 0}
        for payload in indicators.values():
            signal = str(payload.get("signal", "HOLD"))
            if signal == "BUY":
                summary["bullish"] += 1
            elif signal == "SELL":
                summary["bearish"] += 1
            else:
                summary["neutral"] += 1

        return {
            "technical_indicators": indicators,
            "indicator_summary": summary,
            "indicator_charts": charts,
        }

    def _rsi(self, frame: pd.DataFrame, period: int = 14) -> dict[str, Any]:
        delta = frame["close"].diff()
        gains = delta.clip(lower=0).rolling(period).mean()
        losses = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gains / losses.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # Smoothing (Signal line)
        rsi_sma = rsi.rolling(period).mean()
        
        # Weekly RSI approximation
        df_dt = frame.copy()
        df_dt["date_parsed"] = pd.to_datetime(df_dt["date"], errors="coerce")
        df_weekly = df_dt.set_index("date_parsed").resample("W-FRI").agg({"close": "last"}).dropna()
        w_delta = df_weekly["close"].diff()
        w_gains = w_delta.clip(lower=0).rolling(period).mean()
        w_losses = (-w_delta.clip(upper=0)).rolling(period).mean()
        w_rs = w_gains / w_losses.replace(0, np.nan)
        weekly_rsi = 100 - (100 / (1 + w_rs))
        
        df_weekly["weekly_rsi"] = weekly_rsi
        merged = pd.merge(df_dt, df_weekly[["weekly_rsi"]], left_on="date_parsed", right_index=True, how="left")
        merged["weekly_rsi"] = merged["weekly_rsi"].ffill()

        value = self._safe_value(rsi.iloc[-1], fallback=50.0)
        signal = "SELL" if value > 70 else "BUY" if value < 30 else "HOLD"
        
        # Check for divergence
        recent_prices = frame["close"].tail(period)
        recent_rsi = rsi.tail(period)
        price_trend = self._safe_value(recent_prices.iloc[-1]) - self._safe_value(recent_prices.iloc[0])
        rsi_trend = self._safe_value(recent_rsi.iloc[-1]) - self._safe_value(recent_rsi.iloc[0])
        divergence = "None"
        if price_trend > 0 > rsi_trend and value > 50:
            divergence = "Bearish Divergence"
        elif price_trend < 0 < rsi_trend and value < 50:
            divergence = "Bullish Divergence"

        chart_df = frame.copy()
        chart_df["rsi"] = rsi
        chart_df["rsi_sma"] = rsi_sma
        chart_df["weekly_rsi"] = merged["weekly_rsi"]
        
        return {
            "latest": {"value": round(value, 2), "signal": signal, "divergence": divergence},
            "chart": self._multi_line_chart(
                chart_df,
                [
                    ("RSI", chart_df["rsi"]),
                    ("RSI SMA", chart_df["rsi_sma"]),
                    ("Weekly RSI", chart_df["weekly_rsi"]),
                    ("Close", chart_df["close"]),
                    ("Volume", chart_df["volume"]),
                ],
                decimals=2
            ),
        }

    def _moving_averages(self, frame: pd.DataFrame) -> dict[str, Any]:
        ma50 = frame["close"].rolling(50).mean()
        ma200 = frame["close"].rolling(200).mean()
        price = self._safe_value(frame["close"].iloc[-1])
        ma50_value = self._safe_value(ma50.iloc[-1], fallback=price)
        ma200_value = self._safe_value(ma200.iloc[-1], fallback=price)
        if price > ma50_value and price > ma200_value:
            signal = "BUY"
        elif price < ma50_value and price < ma200_value:
            signal = "SELL"
        else:
            signal = "HOLD"
        return {
            "latest": {
                "price": round(price, 2),
                "ma50": round(ma50_value, 2),
                "ma200": round(ma200_value, 2),
                "signal": signal,
            },
            "chart": self._multi_line_chart(
                frame,
                [
                    ("Close", frame["close"]),
                    ("MA 50", ma50),
                    ("MA 200", ma200),
                ],
                decimals=2,
            ),
        }

    def _macd(self, frame: pd.DataFrame) -> dict[str, Any]:
        ema12 = frame["close"].ewm(span=12, adjust=False).mean()
        ema26 = frame["close"].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal_line
        macd_value = self._safe_value(macd.iloc[-1])
        signal_value = self._safe_value(signal_line.iloc[-1])
        signal = "BUY" if macd_value > signal_value else "SELL"
        return {
            "latest": {
                "value": round(macd_value, 4),
                "signal_line": round(signal_value, 4),
                "histogram": round(self._safe_value(histogram.iloc[-1]), 4),
                "signal": signal,
            },
            "chart": self._multi_line_chart(
                frame,
                [("MACD", macd), ("Signal", signal_line), ("Histogram", histogram)],
                decimals=4,
            ),
        }

    def _bollinger_bands(self, frame: pd.DataFrame, period: int = 20) -> dict[str, Any]:
        middle = frame["close"].rolling(period).mean()
        std = frame["close"].rolling(period).std()
        upper = middle + 2 * std
        lower = middle - 2 * std
        price = self._safe_value(frame["close"].iloc[-1])
        upper_value = self._safe_value(upper.iloc[-1], fallback=price)
        lower_value = self._safe_value(lower.iloc[-1], fallback=price)
        middle_value = self._safe_value(middle.iloc[-1], fallback=price)
        band_width = max(upper_value - lower_value, 1e-9)
        upper_distance = abs(price - upper_value) / band_width
        lower_distance = abs(price - lower_value) / band_width
        if upper_distance < 0.12:
            signal = "SELL"
        elif lower_distance < 0.12:
            signal = "BUY"
        else:
            signal = "HOLD"
        return {
            "latest": {
                "price": round(price, 2),
                "middle": round(middle_value, 2),
                "upper": round(upper_value, 2),
                "lower": round(lower_value, 2),
                "signal": signal,
            },
            "chart": self._multi_line_chart(
                frame,
                [("Close", frame["close"]), ("Upper", upper), ("Middle", middle), ("Lower", lower)],
                decimals=2,
            ),
        }

    def _momentum(self, frame: pd.DataFrame, period: int = 10) -> dict[str, Any]:
        momentum = frame["close"] - frame["close"].shift(period)
        value = self._safe_value(momentum.iloc[-1], fallback=0.0)
        signal = "BUY" if value > 0 else "SELL" if value < 0 else "HOLD"
        return {
            "latest": {"value": round(value, 2), "signal": signal},
            "chart": self._single_line_chart(frame, "Momentum", momentum, decimals=2),
        }

    def _atr(self, frame: pd.DataFrame, period: int = 14) -> dict[str, Any]:
        previous_close = frame["close"].shift(1)
        true_range = pd.concat(
            [
                frame["high"] - frame["low"],
                (frame["high"] - previous_close).abs(),
                (frame["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = true_range.rolling(period).mean()
        atr_value = self._safe_value(atr.iloc[-1], fallback=0.0)
        atr_ratio = atr_value / max(self._safe_value(frame["close"].iloc[-1]), 1e-9)
        signal = "HIGH_RISK" if atr_ratio > 0.025 else "LOW_RISK"
        return {
            "latest": {"value": round(atr_value, 4), "signal": signal},
            "chart": self._single_line_chart(frame, "ATR", atr, decimals=4),
        }

    def _stochastic(self, frame: pd.DataFrame, period: int = 14) -> dict[str, Any]:
        highest_high = frame["high"].rolling(period).max()
        lowest_low = frame["low"].rolling(period).min()
        denominator = (highest_high - lowest_low).replace(0, np.nan)
        stochastic = ((frame["close"] - lowest_low) / denominator) * 100
        value = self._safe_value(stochastic.iloc[-1], fallback=50.0)
        signal = "SELL" if value > 80 else "BUY" if value < 20 else "HOLD"
        return {
            "latest": {"value": round(value, 2), "signal": signal},
            "chart": self._single_line_chart(frame, "Stochastic", stochastic, decimals=2),
        }

    def _obv(self, frame: pd.DataFrame) -> dict[str, Any]:
        price_change = frame["close"].diff().fillna(0.0)
        direction = np.sign(price_change)
        obv = (direction * frame["volume"]).fillna(0.0).cumsum()
        latest = self._safe_value(obv.iloc[-1], fallback=0.0)
        previous = self._safe_value(obv.iloc[-2], fallback=latest) if len(obv) > 1 else latest
        signal = "BUY" if latest > previous else "SELL" if latest < previous else "HOLD"
        return {
            "latest": {"value": round(latest, 2), "signal": signal},
            "chart": self._single_line_chart(frame, "OBV", obv, decimals=2),
        }

    def _fibonacci(self, frame: pd.DataFrame, window: int = 30) -> dict[str, Any]:
        recent = frame.tail(window)
        recent_high = self._safe_value(recent["high"].max())
        recent_low = self._safe_value(recent["low"].min())
        spread = max(recent_high - recent_low, 1e-9)
        level_23_6 = recent_high - spread * 0.236
        level_38_2 = recent_high - spread * 0.382
        level_61_8 = recent_high - spread * 0.618
        price = self._safe_value(frame["close"].iloc[-1])
        if abs(price - level_61_8) / max(price, 1e-9) < 0.015:
            signal = "BUY"
        elif abs(price - level_23_6) / max(price, 1e-9) < 0.015:
            signal = "SELL"
        else:
            signal = "HOLD"
        fib_window = frame.tail(min(window, len(frame))).copy()
        fib_window["level_23_6"] = level_23_6
        fib_window["level_38_2"] = level_38_2
        fib_window["level_61_8"] = level_61_8
        return {
            "latest": {
                "price": round(price, 2),
                "level_23_6": round(level_23_6, 2),
                "level_38_2": round(level_38_2, 2),
                "level_61_8": round(level_61_8, 2),
                "signal": signal,
            },
            "chart": self._multi_line_chart(
                fib_window,
                [
                    ("Close", fib_window["close"]),
                    ("23.6%", fib_window["level_23_6"]),
                    ("38.2%", fib_window["level_38_2"]),
                    ("61.8%", fib_window["level_61_8"]),
                ],
                decimals=2,
            ),
        }

    def _adx(self, frame: pd.DataFrame, period: int = 14) -> dict[str, Any]:
        up_move = frame["high"].diff()
        down_move = -frame["low"].diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        previous_close = frame["close"].shift(1)
        true_range = pd.concat(
            [
                frame["high"] - frame["low"],
                (frame["high"] - previous_close).abs(),
                (frame["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = true_range.rolling(period).mean().replace(0, np.nan)
        plus_di = 100 * pd.Series(plus_dm, index=frame.index).rolling(period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=frame.index).rolling(period).mean() / atr
        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
        adx = dx.rolling(period).mean()
        value = self._safe_value(adx.iloc[-1], fallback=20.0)
        signal = "STRONG_TREND" if value > 25 else "WEAK_TREND" if value < 20 else "HOLD"
        return {
            "latest": {"value": round(value, 2), "signal": signal},
            "chart": self._single_line_chart(frame, "ADX", adx, decimals=2),
        }

    def _single_line_chart(
        self,
        frame: pd.DataFrame,
        label: str,
        series: pd.Series,
        *,
        decimals: int,
        limit: int = 60,
    ) -> dict[str, Any]:
        window = pd.DataFrame({"date": frame["date"], "value": series}).tail(limit)
        points = [
            {
                "date": str(row.date),
                "value": round(float(row.value), decimals),
            }
            for row in window.itertuples(index=False)
            if pd.notna(row.value)
        ]
        return {"type": "line", "series": [{"label": label, "points": points}]}

    def _multi_line_chart(
        self,
        frame: pd.DataFrame,
        lines: list[tuple[str, pd.Series]],
        *,
        decimals: int,
        limit: int = 60,
    ) -> dict[str, Any]:
        chart_series = []
        dates = frame["date"].tail(limit).tolist()
        for label, values in lines:
            aligned = values.tail(limit).tolist()
            points = []
            for date_value, point_value in zip(dates, aligned, strict=False):
                if pd.isna(point_value):
                    continue
                points.append({"date": str(date_value), "value": round(float(point_value), decimals)})
            chart_series.append({"label": label, "points": points})
        return {"type": "line", "series": chart_series}

    @staticmethod
    def _safe_value(value: Any, fallback: float = 0.0) -> float:
        if value is None or pd.isna(value):
            return float(fallback)
        return float(value)
