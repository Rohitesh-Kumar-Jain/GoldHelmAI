from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReasoningInput:
    prediction: float
    current_price: float
    sentiment_score: float
    sentiment_label: str
    momentum_7: float
    predicted_change_pct: float
    base_confidence: float


class ReasoningAgent:
    """Interprets model outputs into a trade stance and human-readable analysis."""

    def reason(self, payload: ReasoningInput) -> dict[str, object]:
        decision = self._decide(payload)
        confidence = self._confidence(payload, decision)
        analysis = self._analysis(payload, decision)
        return {
            "decision": decision,
            "confidence": round(confidence, 4),
            "analysis": analysis,
        }

    @staticmethod
    def _decide(payload: ReasoningInput) -> str:
        if payload.prediction > payload.current_price and payload.sentiment_label == "positive":
            return "BUY"
        if payload.prediction < payload.current_price and payload.sentiment_label == "negative":
            return "SELL"
        return "HOLD"

    @staticmethod
    def _confidence(payload: ReasoningInput, decision: str) -> float:
        confidence = payload.base_confidence

        if decision != "HOLD":
            confidence += 0.08
        if abs(payload.sentiment_score) >= 0.25:
            confidence += 0.05
        if abs(payload.predicted_change_pct) >= 1.0:
            confidence += 0.04
        if payload.momentum_7 > 0 and decision == "BUY":
            confidence += 0.03
        if payload.momentum_7 < 0 and decision == "SELL":
            confidence += 0.03
        if decision == "HOLD":
            confidence -= 0.05

        return max(0.5, min(confidence, 0.97))

    @staticmethod
    def _analysis(payload: ReasoningInput, decision: str) -> list[str]:
        analysis: list[str] = []

        if payload.prediction > payload.current_price:
            analysis.append("Model predicts upward movement from the latest close.")
        elif payload.prediction < payload.current_price:
            analysis.append("Model predicts downside from the latest close.")
        else:
            analysis.append("Model predicts limited change from the latest close.")

        if payload.sentiment_label == "positive":
            analysis.append("Market sentiment is positive across recent gold-related news.")
        elif payload.sentiment_label == "negative":
            analysis.append("Market sentiment is negative across recent gold-related news.")
        else:
            analysis.append("Market sentiment is neutral, so the model leans on price structure.")

        if payload.momentum_7 > 0:
            analysis.append("Momentum indicators remain bullish over the short term.")
        elif payload.momentum_7 < 0:
            analysis.append("Momentum indicators remain soft over the short term.")
        else:
            analysis.append("Momentum indicators are balanced over the short term.")

        if decision == "BUY":
            analysis.append("The reasoning layer recommends BUY because price direction and sentiment align.")
        elif decision == "SELL":
            analysis.append("The reasoning layer recommends SELL because price direction and sentiment align lower.")
        else:
            analysis.append("The reasoning layer recommends HOLD because the signals are mixed.")

        return analysis
