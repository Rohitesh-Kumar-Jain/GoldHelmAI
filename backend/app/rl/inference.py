from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.rl.agent import QLearningTradingAgent
from app.utils.config import get_settings


ACTION_TO_DECISION = {
    0: "HOLD",
    1: "BUY",
    2: "SELL",
}


class RLInferenceService:
    """Loads a trained RL policy and produces fast trading decisions."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cached_model: tuple[QLearningTradingAgent, dict[str, float]] | None = None

    def infer(self, current_price: float, prediction: float, sentiment_score: float) -> dict[str, Any]:
        model_bundle = self._load_model()
        state = np.array([current_price, prediction, sentiment_score], dtype=float)

        if model_bundle is None:
            return self._fallback_decision(current_price, prediction, sentiment_score)

        agent, metadata = model_bundle
        action = agent.choose_action(state, explore=False)
        q_values = agent.q_values(state)
        confidence = self._confidence_from_q_values(q_values)
        decision = ACTION_TO_DECISION[action]

        return {
            "rl_decision": decision,
            "rl_confidence": round(confidence, 4),
            "policy_source": "q_learning",
            "backtest": {
                "total_return": float(metadata.get("total_return", 0.0)),
                "number_of_trades": float(metadata.get("number_of_trades", 0.0)),
                "win_rate": float(metadata.get("win_rate", 0.0)),
                "final_portfolio_value": float(metadata.get("final_portfolio_value", 0.0)),
                "sharpe_ratio": float(metadata.get("sharpe_ratio", 0.0)),
                "max_drawdown": float(metadata.get("max_drawdown", 0.0)),
            },
        }

    def _load_model(self) -> tuple[QLearningTradingAgent, dict[str, float]] | None:
        if self._cached_model is not None:
            return self._cached_model

        model_path = Path(self.settings.rl_model_path)
        if not model_path.exists():
            return None

        self._cached_model = QLearningTradingAgent.load(model_path)
        return self._cached_model

    @staticmethod
    def _fallback_decision(current_price: float, prediction: float, sentiment_score: float) -> dict[str, Any]:
        if prediction > current_price and sentiment_score > 0.15:
            decision = "BUY"
        elif prediction < current_price and sentiment_score < -0.15:
            decision = "SELL"
        else:
            decision = "HOLD"

        return {
            "rl_decision": decision,
            "rl_confidence": 0.58,
            "policy_source": "fallback_rule",
            "backtest": {
                "total_return": 0.0,
                "number_of_trades": 0.0,
                "win_rate": 0.0,
                "final_portfolio_value": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
            },
        }

    @staticmethod
    def _confidence_from_q_values(q_values: np.ndarray) -> float:
        ordered = np.sort(q_values)
        if len(ordered) < 2:
            return 0.55

        edge = float(ordered[-1] - ordered[-2])
        return max(0.5, min(0.92, 0.55 + edge / 10.0))
