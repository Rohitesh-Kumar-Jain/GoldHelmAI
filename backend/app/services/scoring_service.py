from typing import Any

INDICATOR_WEIGHTS = {
    # Trend (40)
    "ma": 15,
    "macd": 15,
    "adx": 10,

    # Momentum (30)
    "rsi": 10,
    "stochastic": 10,
    "momentum": 10,

    # Volatility (15)
    "bollinger": 10,
    "atr": 5,

    # Structure (15)
    "obv": 5,
    "fibonacci": 10
}

class ScoringService:
    """
    Production-grade Technical Indicator Scoring Engine.
    Converts technical indicators into a single interpretable score [-100, 100].
    """

    @staticmethod
    def _get_binary_signal(indicator_payload: dict[str, Any]) -> int:
        """Helper to convert signals to binary +1, 0, -1."""
        if not indicator_payload:
            return 0
        sig = str(indicator_payload.get("signal", "HOLD")).upper()
        if "BUY" in sig:
            return 1
        if "SELL" in sig:
            return -1
        return 0

    @staticmethod
    def compute_score(current_price: float, indicators: dict[str, Any]) -> dict[str, Any]:
        if current_price <= 0:
            raise ValueError("current_price must be > 0 calculation requires positive price.")
        if not indicators:
            raise ValueError("technical_indicators cannot be empty.")

        # --- A. Continuous Signals (Clamp to [-1, 1]) ---
        rsi_val = float(indicators.get("rsi", {}).get("value", 50.0))
        rsi_score = max(-1.0, min(1.0, (rsi_val - 50.0) / 50.0))

        stoch_val = float(indicators.get("stochastic", {}).get("value", 50.0))
        stoch_score = max(-1.0, min(1.0, (stoch_val - 50.0) / 50.0))

        # --- B. Binary Signals ---
        # NOTE: MA and MACD are correlated trend indicators.
        # This may overweight trend signals in strong markets.
        # Consider correlation penalties in future versions.
        ma_signal = ScoringService._get_binary_signal(indicators.get("moving_averages", {}))
        macd_signal = ScoringService._get_binary_signal(indicators.get("macd", {}))
        mom_signal = ScoringService._get_binary_signal(indicators.get("momentum", {}))
        bb_signal = ScoringService._get_binary_signal(indicators.get("bollinger_bands", {}))
        obv_signal = ScoringService._get_binary_signal(indicators.get("obv", {}))
        fib_signal = ScoringService._get_binary_signal(indicators.get("fibonacci", {}))

        # --- C. Compute Category Scores ---
        # Trend
        # ADX is not a binary directional signal, but trend strength. Handled explicitly in score adjustment later, 
        # or we omit it from the direct trend multiplication and apply it globally. 
        # Per instructions: `Instead of multiplying: If adx_value > 25: score += 5 elif adx_value < 20: score -= 5`
        # We will calculate trend score without 10*adx binary, and adjust the total later.
        trend_score = (INDICATOR_WEIGHTS["ma"] * ma_signal) + (INDICATOR_WEIGHTS["macd"] * macd_signal)

        # Momentum
        momentum_score = (
            (INDICATOR_WEIGHTS["rsi"] * rsi_score) + 
            (INDICATOR_WEIGHTS["stochastic"] * stoch_score) + 
            (INDICATOR_WEIGHTS["momentum"] * mom_signal)
        )

        # Volatility
        volatility_score = INDICATOR_WEIGHTS["bollinger"] * bb_signal

        # Structure
        structure_score = (INDICATOR_WEIGHTS["obv"] * obv_signal) + (INDICATOR_WEIGHTS["fibonacci"] * fib_signal)

        # --- D. Combine ---
        score = trend_score + momentum_score + volatility_score + structure_score

        # --- E. ADX Adjustment (Safe Approach) ---
        adx_val = float(indicators.get("adx", {}).get("value", 20.0))
        if adx_val > 25:
            score += 5.0
        elif adx_val < 20:
            score -= 5.0

        # --- F. ATR Normalization (CRITICAL FIX) ---
        atr_val = float(indicators.get("atr", {}).get("value", 0.0))
        atr_pct = atr_val / current_price
        volatility_adjustment = 1.0
        if atr_pct > 0.02:
            volatility_adjustment = 0.8
            score *= 0.8

        # --- G. Clamp Final Score ---
        score = max(min(score, 100.0), -100.0)

        # --- H. Compute Confidence ---
        confidence = abs(score) / 100.0

        # --- I. Map to Signal ---
        if score > 60:
            signal_text = "STRONG BUY"
        elif score > 20:
            signal_text = "BUY"
        elif score > -20:
            signal_text = "HOLD"
        elif score > -60:
            signal_text = "SELL"
        else:
            signal_text = "STRONG SELL"

        return {
            "score": round(score, 2),
            "signal": signal_text,
            "confidence": round(confidence, 4),
            "breakdown": {
                "trend": round(trend_score, 2),
                "momentum": round(momentum_score, 2),
                "volatility_adjustment": round(volatility_adjustment, 2),
                "structure": round(structure_score, 2)
            }
        }
