from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class IndicatorService:
    """Computes technical indicators, summary counts, and chart-ready series."""

    def compute_indicators(self, frame: pd.DataFrame) -> dict[str, Any]:
        market = frame.copy()
        market["date_parsed"] = pd.to_datetime(market["date"], errors="coerce")
        market["close"] = pd.to_numeric(market["close"], errors="coerce")
        market["open"] = pd.to_numeric(market.get("open", market["close"]), errors="coerce")
        market["high"] = pd.to_numeric(market.get("high", market["close"]), errors="coerce")
        market["low"] = pd.to_numeric(market.get("low", market["close"]), errors="coerce")
        market["volume"] = pd.to_numeric(market.get("volume", 0.0), errors="coerce").fillna(0.0)
        market = market.dropna(subset=["close", "high", "low"]).reset_index(drop=True)

        if market.empty:
            return {
                "technical_indicators": {},
                "indicator_summary": {"bullish": 0, "bearish": 0, "neutral": 0, "score": 0, "conflicting_signals": []},
                "indicator_charts": {},
                "special_flags": {}
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

        def _get_sig_val(sig: str) -> float:
            if "STRONG_BUY" in sig or "BUY" in sig: return 1.0
            if "STRONG_SELL" in sig or "SELL" in sig: return -1.0
            return 0.0

        trend_score = (_get_sig_val(indicators["moving_averages"]["signal"]) + _get_sig_val(indicators["macd"]["signal"]) + _get_sig_val(indicators["adx"]["signal"])) / 3.0
        momentum_score = (_get_sig_val(indicators["rsi"]["signal"]) + _get_sig_val(indicators["stochastic"]["signal"]) + _get_sig_val(indicators["momentum"]["signal"])) / 3.0
        volume_score = _get_sig_val(indicators["obv"]["signal"])

        composite_score = (trend_score * 0.5) + (momentum_score * 0.3) + (volume_score * 0.2)

        conflicting_signals = []
        if trend_score > 0.3 and momentum_score < -0.3:
            conflicting_signals.append("Trend is Up, but Momentum is Down (Possible Exhaustion)")
        elif trend_score < -0.3 and momentum_score > 0.3:
            conflicting_signals.append("Trend is Down, but Momentum is Up (Possible Bottoming)")

        df_weekly = market.set_index("date_parsed").resample("W-FRI").agg({"date": "last", "close": "last", "open": "first", "high": "max", "low": "min", "volume": "sum"}).dropna().reset_index(drop=True)
        weekly_ma = self._moving_averages(df_weekly) if len(df_weekly) > 0 else moving_averages
        weekly_macd = self._macd(df_weekly) if len(df_weekly) > 0 else macd
        weekly_trend_score = (_get_sig_val(weekly_ma["latest"]["signal"]) + _get_sig_val(weekly_macd["latest"]["signal"])) / 2.0
        timeframe_alignment = bool(np.sign(trend_score) == np.sign(weekly_trend_score) if abs(trend_score) > 0 and abs(weekly_trend_score) > 0 else False)

        rsi_val = indicators["rsi"]["value"]
        adx_val = indicators["adx"]["value"]
        mom_val = indicators["momentum"]["value"]
        macd_val = indicators["macd"]["value"]
        macd_sig = indicators["macd"]["signal_line"]
        
        falling_knife = bool(adx_val > 25 and rsi_val < 35)
        dead_cat_bounce = bool(mom_val < 0 and rsi_val > 30 and macd_val <= macd_sig)
        
        summary = {
            "bullish": sum(1 for p in indicators.values() if "BUY" in str(p.get("signal", ""))),
            "bearish": sum(1 for p in indicators.values() if "SELL" in str(p.get("signal", ""))),
            "neutral": sum(1 for p in indicators.values() if "HOLD" in str(p.get("signal", ""))),
            "score": composite_score,
            "conflicting_signals": conflicting_signals
        }

        return {
            "technical_indicators": indicators,
            "indicator_summary": summary,
            "indicator_charts": charts,
            "special_flags": {
                "falling_knife": falling_knife,
                "dead_cat_bounce": dead_cat_bounce,
                "timeframe_alignment": timeframe_alignment
            }
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
        
        # Algorithmic divergence (rolling window peak/trough sequence)
        recent_window = 20
        recent_prices = frame["close"].tail(recent_window).tolist()
        recent_rsi = rsi.tail(recent_window).tolist()
        divergence = "None"
        if len(recent_prices) == recent_window:
            p_min_idx = np.argmin(recent_prices)
            r_min_idx = np.argmin(recent_rsi)
            p_max_idx = np.argmax(recent_prices)
            r_max_idx = np.argmax(recent_rsi)
            
            # Bullish divergence: price made lower low, RSI made higher low (min index disparity)
            if p_min_idx > r_min_idx and recent_prices[-1] < np.mean(recent_prices):
                if recent_rsi[-1] > recent_rsi[r_min_idx]:
                    divergence = "Bullish Divergence"
            # Bearish divergence: price made higher high, RSI made lower high
            if p_max_idx > r_max_idx and recent_prices[-1] > np.mean(recent_prices):
                if recent_rsi[-1] < recent_rsi[r_max_idx]:
                    divergence = "Bearish Divergence"

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
                    ("Volume", chart_df["volume"]),
                ],
                decimals=2,
                include_candlestick=True,
            ),
        }

    def _moving_averages(self, frame: pd.DataFrame) -> dict[str, Any]:
        ma50 = frame["close"].rolling(50).mean()
        ma200 = frame["close"].rolling(200).mean()
        price = self._safe_value(frame["close"].iloc[-1])
        ma50_value = self._safe_value(ma50.iloc[-1], fallback=price)
        ma200_value = self._safe_value(ma200.iloc[-1], fallback=price)
        
        golden_cross = (ma50.iloc[-1] > ma200.iloc[-1]) and (len(ma50) > 1 and ma50.iloc[-2] <= ma200.iloc[-2])
        death_cross = (ma50.iloc[-1] < ma200.iloc[-1]) and (len(ma50) > 1 and ma50.iloc[-2] >= ma200.iloc[-2])
        
        distance_to_200 = abs(price - ma200_value) / max(ma200_value, 1e-9)
        distance_to_50 = (price - ma50_value) / max(ma50_value, 1e-9)

        signal = "HOLD"
        message = "Mixed trend signals"
        if golden_cross:
            signal = "STRONG_BUY"
            message = "Golden Cross Formed"
        elif death_cross:
            signal = "STRONG_SELL"
            message = "Death Cross Formed"
        elif distance_to_200 < 0.01:
            signal = "HOLD" if price > ma50_value else "SELL"
            message = "Testing MA200 Support/Resistance"
        elif price < ma50_value and price < ma200_value:
            signal = "SELL"
            if distance_to_50 < -0.05:
                signal = "STRONG_SELL"
                message = f"Deeply below MA50 by {abs(distance_to_50)*100:.1f}%. Clear breakdown."
            else:
                message = "Price is below both MA50 and MA200. Trend weakness."
        elif price > ma50_value and price > ma200_value:
            signal = "BUY"
            message = "Fully Aligned Uptrend"

        return {
            "latest": {
                "price": round(price, 2),
                "ma50": round(ma50_value, 2),
                "ma200": round(ma200_value, 2),
                "signal": signal,
                "message": message,
            },
            "chart": self._multi_line_chart(
                frame,
                [
                    ("MA 50", ma50),
                    ("MA 200", ma200),
                ],
                decimals=2,
                include_candlestick=True,
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
        macd_prev = self._safe_value(macd.iloc[-2]) if len(macd) > 1 else macd_value

        signal = "BUY" if macd_value > signal_value else "SELL"
        message = "Improving upside momentum" if signal == "BUY" else "Fading momentum or bearish crossover"

        if macd_value > 0 and macd_prev <= 0:
            signal = "STRONG_BUY"
            message = "Bullish Zero-Line Crossover"
        elif macd_value < 0 and macd_prev >= 0:
            signal = "STRONG_SELL"
            message = "Bearish Zero-Line Crossover"
        elif macd_value < 0 and signal_value < 0:
            if signal == "SELL":
                signal = "STRONG_SELL"
                message = "Deeply Negative Breakdown"
                
        return {
            "latest": {
                "value": round(macd_value, 4),
                "signal_line": round(signal_value, 4),
                "histogram": round(self._safe_value(histogram.iloc[-1]), 4),
                "signal": signal,
                "message": message,
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
        pct_b = (price - lower_value) / band_width

        message = f"Trading inside bands (%B = {pct_b:.2f})"
        signal = "HOLD"
        
        if pct_b < 0:
            signal = "STRONG_SELL"
            message = f"Pierced Lower Band (%B = {pct_b:.2f}) - Breakdown or extreme oversold"
        elif pct_b > 1:
            signal = "STRONG_BUY"
            message = f"Pierced Upper Band (%B = {pct_b:.2f}) - Breakout or extreme overbought"
        elif pct_b < 0.12:
            signal = "SELL"
            message = "Approaching Lower Band" if band_width/price > 0.05 else "Squeeze near Lower Band"
        elif pct_b > 0.88:
            signal = "BUY"
            message = "Approaching Upper Band" if band_width/price > 0.05 else "Squeeze near Upper Band"

        return {
            "latest": {
                "price": round(price, 2),
                "middle": round(middle_value, 2),
                "upper": round(upper_value, 2),
                "lower": round(lower_value, 2),
                "signal": signal,
                "message": message,
            },
            "chart": self._multi_line_chart(
                frame,
                [("Upper", upper), ("Middle", middle), ("Lower", lower)],
                decimals=2,
                include_candlestick=True,
            ),
        }

    def _momentum(self, frame: pd.DataFrame, period: int = 10) -> dict[str, Any]:
        momentum = frame["close"] - frame["close"].shift(period)
        value = self._safe_value(momentum.iloc[-1], fallback=0.0)
        signal = "BUY" if value > 0 else "SELL" if value < 0 else "HOLD"
        return {
            "latest": {"value": round(value, 2), "signal": signal},
            "chart": self._multi_line_chart(frame, [("Momentum", momentum)], decimals=2, include_candlestick=True),
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
        price = self._safe_value(frame["close"].iloc[-1])
        return {
            "latest": {
                "value": round(atr_value, 4), 
                "signal": signal,
                "stop_1x": round(price - atr_value, 2) if price > 0 else 0,
                "stop_1_5x": round(price - (1.5 * atr_value), 2) if price > 0 else 0,
                "stop_2x": round(price - (2 * atr_value), 2) if price > 0 else 0,
            },
            "chart": self._multi_line_chart(frame, [("ATR", atr)], decimals=4, include_candlestick=True),
        }

    def _stochastic(self, frame: pd.DataFrame, period: int = 14) -> dict[str, Any]:
        highest_high = frame["high"].rolling(period).max()
        lowest_low = frame["low"].rolling(period).min()
        denominator = (highest_high - lowest_low).replace(0, np.nan)
        k_line = ((frame["close"] - lowest_low) / denominator) * 100
        d_line = k_line.rolling(3).mean()
        
        k_val = self._safe_value(k_line.iloc[-1], fallback=50.0)
        d_val = self._safe_value(d_line.iloc[-1], fallback=50.0)
        k_prev = self._safe_value(k_line.iloc[-2], fallback=k_val) if len(k_line) > 1 else k_val
        d_prev = self._safe_value(d_line.iloc[-2], fallback=d_val) if len(d_line) > 1 else d_val

        signal = "HOLD"
        message = "Neutral"
        if k_val > 80: signal = "SELL"
        elif k_val < 20: signal = "BUY"
        
        # Crossover detection
        if k_val > d_val and k_prev <= d_prev:
            signal = "STRONG_BUY" if k_val < 30 else "BUY"
            message = "Bullish %K/%D Crossover"
        elif k_val < d_val and k_prev >= d_prev:
            signal = "STRONG_SELL" if k_val > 70 else "SELL"
            message = "Bearish %K/%D Crossover"

        return {
            "latest": {"value": round(k_val, 2), "d_value": round(d_val, 2), "signal": signal, "message": message},
            "chart": self._multi_line_chart(frame, [("%K", k_line), ("%D", d_line)], decimals=2, include_candlestick=True),
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
            "chart": self._multi_line_chart(frame, [("OBV", obv)], decimals=2, include_candlestick=True),
        }

    def _fibonacci(self, frame: pd.DataFrame, window: int = 30) -> dict[str, Any]:
        recent = frame.tail(window)
        recent_high = self._safe_value(recent["high"].max())
        recent_low = self._safe_value(recent["low"].min())
        spread = max(recent_high - recent_low, 1e-9)
        level_23_6 = recent_high - spread * 0.236
        level_38_2 = recent_high - spread * 0.382
        level_50_0 = recent_high - spread * 0.500
        level_61_8 = recent_high - spread * 0.618
        level_78_6 = recent_high - spread * 0.786
        price = self._safe_value(frame["close"].iloc[-1])
        
        signal = "HOLD"
        message = "Trading between levels"
        # Logic to detect breaks
        if price < level_78_6:
            signal = "STRONG_SELL"
            message = "Broken below 78.6% Retracement"
        elif price < level_61_8:
            signal = "SELL"
            message = "Broken below 61.8% Retracement"
        elif price < level_50_0:
            signal = "HOLD"
            message = "Broken below 50.0% Retracement"
        elif price < level_38_2:
            signal = "HOLD"
            message = "Broken below 38.2% Retracement"
        elif price < level_23_6:
            signal = "HOLD"
            message = "Broken below 23.6% Retracement"

        if abs(price - level_61_8) / max(price, 1e-9) < 0.015:
            signal = "BUY"
            message = "Testing 61.8% Support"

        fib_window = frame.tail(min(window, len(frame))).copy()
        fib_window["level_23_6"] = level_23_6
        fib_window["level_38_2"] = level_38_2
        fib_window["level_50_0"] = level_50_0
        fib_window["level_61_8"] = level_61_8
        fib_window["level_78_6"] = level_78_6
        return {
            "latest": {
                "price": round(price, 2),
                "signal": signal,
                "message": message,
            },
            "chart": self._multi_line_chart(
                fib_window,
                [
                    ("23.6%", fib_window["level_23_6"]),
                    ("38.2%", fib_window["level_38_2"]),
                    ("50.0%", fib_window["level_50_0"]),
                    ("61.8%", fib_window["level_61_8"]),
                    ("78.6%", fib_window["level_78_6"]),
                ],
                decimals=2,
                include_candlestick=True,
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
        plus_di_val = self._safe_value(plus_di.iloc[-1])
        minus_di_val = self._safe_value(minus_di.iloc[-1])

        trend_dir = "BUY" if plus_di_val > minus_di_val else "SELL"
        signal = f"STRONG_{trend_dir}" if value > 25 else "HOLD"
        
        return {
            "latest": {"value": round(value, 2), "signal": signal, "message": f"+DI: {plus_di_val:.1f}, -DI: {minus_di_val:.1f}"},
            "chart": self._multi_line_chart(frame, [("ADX", adx), ("+DI", plus_di), ("-DI", minus_di)], decimals=2, include_candlestick=True),
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
        include_candlestick: bool = False,
    ) -> dict[str, Any]:
        chart_series = []
        window = frame.tail(limit)
        dates = window["date"].tolist()
        
        if include_candlestick:
            opens = window.get("open", window["close"]).tolist()
            highs = window.get("high", window["close"]).tolist()
            lows = window.get("low", window["close"]).tolist()
            closes = window["close"].tolist()
            points = []
            for d, o, h, l, c in zip(dates, opens, highs, lows, closes, strict=False):
                if pd.isna(c):
                    continue
                points.append({
                    "date": str(d), 
                    "value": round(float(c), decimals),
                    "open": round(float(o), decimals),
                    "high": round(float(h), decimals),
                    "low": round(float(l), decimals),
                    "close": round(float(c), decimals)
                })
            chart_series.append({"label": "Candles", "points": points})

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
