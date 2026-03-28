from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from app.agents.reasoning_agent import ReasoningAgent, ReasoningInput
from app.rl.inference import RLInferenceService
from app.services.data_service import GoldDataService
from app.services.feature_service import FeatureEngineeringService
from app.services.indicator_service import IndicatorService
from app.services.news_service import NewsService
from app.services.sentiment_service import SentimentService
from app.utils.config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class ModelArtifacts:
    model: RandomForestRegressor
    feature_frame: pd.DataFrame
    validation_mae: float
    cache_key: str


class PredictionService:
    """Trains a compact regression model and predicts the next trading-day close."""

    def __init__(
        self,
        data_service: GoldDataService,
        news_service: NewsService | None = None,
        sentiment_service: SentimentService | None = None,
        reasoning_agent: ReasoningAgent | None = None,
        rl_inference_service: RLInferenceService | None = None,
        indicator_service: IndicatorService | None = None,
    ) -> None:
        self.data_service = data_service
        self.news_service = news_service or NewsService()
        self.sentiment_service = sentiment_service or SentimentService()
        self.reasoning_agent = reasoning_agent or ReasoningAgent()
        self.rl_inference_service = rl_inference_service or RLInferenceService()
        self.indicator_service = indicator_service or IndicatorService()
        self.feature_service = FeatureEngineeringService()
        self.settings = get_settings()
        self.feature_columns = [
            "close",
            "lag_1",
            "lag_2",
            "ma7",
            "ma14",
            "ma30",
            "returns",
            "volatility",
            "momentum_7",
            "momentum_14",
            "sentiment_score",
        ]
        self._cached_artifacts: ModelArtifacts | None = None

    def predict_next_day(self) -> dict[str, Any] | None:
        raw = self.data_service.get_training_frame()
        indicator_payload = self.indicator_service.compute_indicators(raw)
        news_articles = self.news_service.get_latest_news()
        sentiment = self.sentiment_service.analyze_articles(news_articles)
        sentiment_series = self.sentiment_service.build_daily_sentiment_series(
            news_articles,
            pd.to_datetime(raw["date"], errors="coerce"),
        )
        feature_frame = self.feature_service.build_features(raw, sentiment_series=sentiment_series)

        if len(feature_frame) < self.settings.model_min_rows:
            logger.info(
                "Skipping prediction because only %s feature rows are available.",
                len(feature_frame),
            )
            return None

        artifacts = self._get_or_train_artifacts(feature_frame, sentiment)
        latest_row = artifacts.feature_frame.iloc[-1]
        last_close = float(latest_row["close"])
        predicted_return = float(
            artifacts.model.predict(latest_row[self.feature_columns].to_frame().T)[0]
        )
        predicted_return = float(np.clip(predicted_return, -0.05, 0.05))
        prediction = max(0.0, last_close * (1.0 + predicted_return))
        base_confidence = self._estimate_confidence(artifacts.validation_mae, last_close)
        reasoning = self.reasoning_agent.reason(
            ReasoningInput(
                prediction=prediction,
                current_price=last_close,
                sentiment_score=float(sentiment["sentiment_score"]),
                sentiment_label=sentiment["label"],
                momentum_7=float(latest_row["momentum_7"]),
                predicted_change_pct=predicted_return * 100,
                base_confidence=base_confidence,
            )
        )
        rl_result = self.rl_inference_service.infer(
            current_price=last_close,
            prediction=prediction,
            sentiment_score=float(sentiment["sentiment_score"]),
        )
        final_decision = self._finalize_decision(
            reasoning_decision=str(reasoning["decision"]),
            rl_decision=str(rl_result["rl_decision"]),
            reasoning_confidence=float(reasoning["confidence"]),
            rl_confidence=float(rl_result["rl_confidence"]),
        )
        agreement = reasoning["decision"] == rl_result["rl_decision"]
        final_analysis = self._finalize_analysis(
            predicted_change_pct=predicted_return * 100,
            sentiment_label=sentiment["label"],
            reasoning_decision=str(reasoning["decision"]),
            final_decision=final_decision,
            rl_decision=str(rl_result["rl_decision"]),
            agreement=agreement,
            policy_source=str(rl_result["policy_source"]),
        )
        final_confidence = self._merge_confidence(
            reasoning_confidence=float(reasoning["confidence"]),
            rl_confidence=float(rl_result["rl_confidence"]),
            aligned=agreement and final_decision == reasoning["decision"],
        )
        risk_level = self._risk_level(
            volatility=float(latest_row["volatility"]),
            disagreement=not agreement,
        )

        logger.info(
            "Prediction generated: current=%s prediction=%s sentiment=%s reasoning=%s rl=%s final=%s risk=%s",
            round(last_close, 2),
            round(prediction, 2),
            sentiment["label"],
            reasoning["decision"],
            rl_result["rl_decision"],
            final_decision,
            risk_level,
        )

        return {
            "ticker": self.data_service.ticker,
            "as_of": str(latest_row["date"].date()),
            "current_price": round(last_close, 2),
            "prediction": round(prediction, 2),
            "predicted_change_pct": round(predicted_return * 100, 3),
            "decision": final_decision,
            "rl_decision": rl_result["rl_decision"],
            "confidence": round(final_confidence, 4),
            "model": "random_forest_next_day_return",
            "validation_mae": round(artifacts.validation_mae, 2),
            "risk_level": risk_level,
            "sentiment": {
                "score": round(float(sentiment["sentiment_score"]), 4),
                "label": sentiment["label"],
            },
            "technical_indicators": indicator_payload["technical_indicators"],
            "indicator_summary": indicator_payload["indicator_summary"],
            "indicator_charts": indicator_payload["indicator_charts"],
            "debate": {
                "reasoning_agent": {
                    "decision": reasoning["decision"],
                    "confidence": reasoning["confidence"],
                },
                "rl_agent": {
                    "decision": rl_result["rl_decision"],
                    "confidence": rl_result["rl_confidence"],
                },
                "policy_source": rl_result["policy_source"],
                "agreement": reasoning["decision"] == rl_result["rl_decision"],
            },
            "backtest": rl_result["backtest"],
            "final_analysis": final_analysis,
        }

    def get_latest_sentiment(self) -> dict[str, Any]:
        articles = self.news_service.get_latest_news()
        sentiment = self.sentiment_service.analyze_articles(articles)
        return {
            "score": round(float(sentiment["sentiment_score"]), 4),
            "label": sentiment["label"],
            "article_count": sentiment["article_count"],
            "articles": articles,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _get_or_train_artifacts(
        self,
        feature_frame: pd.DataFrame,
        sentiment: dict[str, Any],
    ) -> ModelArtifacts:
        latest_date = str(feature_frame.iloc[-1]["date"].date())
        cache_key = f"{latest_date}:{round(float(sentiment['sentiment_score']), 4)}:{sentiment['article_count']}"
        if self._cached_artifacts and self._cached_artifacts.cache_key == cache_key:
            return self._cached_artifacts

        artifacts = self._train_model(feature_frame, cache_key=cache_key)
        self._cached_artifacts = artifacts
        return artifacts

    def _train_model(self, feature_frame: pd.DataFrame, cache_key: str) -> ModelArtifacts:
        dataset = feature_frame.copy()
        split_index = max(int(len(dataset) * 0.8), self.settings.model_min_rows - 1)
        split_index = min(split_index, len(dataset) - 1)

        train_frame = dataset.iloc[:split_index].copy()
        validation_frame = dataset.iloc[split_index:].copy()
        if train_frame.empty or validation_frame.empty:
            raise ValueError("Insufficient rows to create train and validation splits.")

        model = RandomForestRegressor(
            n_estimators=300,
            random_state=self.settings.model_random_state,
            max_depth=8,
            min_samples_leaf=2,
        )
        model.fit(train_frame[self.feature_columns], train_frame["target_return"])

        validation_predictions = model.predict(validation_frame[self.feature_columns])
        validation_actual_prices = validation_frame["close"] * (1.0 + validation_frame["target_return"])
        validation_predicted_prices = validation_frame["close"] * (1.0 + validation_predictions)
        validation_mae = float(
            mean_absolute_error(validation_actual_prices, validation_predicted_prices)
        )

        logger.info(
            "Trained prediction model on %s rows with validation MAE %.2f.",
            len(train_frame),
            validation_mae,
        )
        return ModelArtifacts(
            model=model,
            feature_frame=dataset,
            validation_mae=validation_mae,
            cache_key=cache_key,
        )

    @staticmethod
    def _estimate_confidence(validation_mae: float, reference_price: float) -> float:
        if reference_price <= 0:
            return 0.5

        relative_error = validation_mae / reference_price
        confidence = 1.0 - min(relative_error * 4.0, 0.45)
        return max(0.55, confidence)

    @staticmethod
    def _finalize_decision(
        reasoning_decision: str,
        rl_decision: str,
        reasoning_confidence: float,
        rl_confidence: float,
    ) -> str:
        if reasoning_decision == rl_decision:
            return reasoning_decision

        if rl_confidence > 0.9:
            return rl_decision

        if reasoning_confidence >= 0.85 and rl_confidence <= 0.65:
            return reasoning_decision

        if reasoning_confidence < 0.75 and rl_confidence < 0.75:
            return "HOLD"

        return "HOLD"

    @staticmethod
    def _merge_confidence(reasoning_confidence: float, rl_confidence: float, aligned: bool) -> float:
        base = (reasoning_confidence + rl_confidence) / 2.0
        if aligned:
            base += 0.04
        else:
            base *= 0.6
        return max(0.5, min(base, 0.97))

    @staticmethod
    def _finalize_analysis(
        predicted_change_pct: float,
        sentiment_label: str,
        reasoning_decision: str,
        final_decision: str,
        rl_decision: str,
        agreement: bool,
        policy_source: str,
    ) -> list[str]:
        direction = "upward" if predicted_change_pct >= 0 else "downward"
        analysis = [
            f"ML model predicts {predicted_change_pct:.2f}% {direction} movement.",
            f"Sentiment is {sentiment_label}, providing {'support' if sentiment_label != 'neutral' else 'weak confirmation'}.",
        ]

        if agreement:
            analysis.append(f"Reasoning and RL agents agree on {final_decision}.")
        else:
            analysis.append(
                f"RL agent suggests {rl_decision}, indicating a possible short-term reversal versus the {reasoning_decision} reasoning view."
            )
            analysis.append("Final decision is HOLD due to conflicting signals.")

        if final_decision != "HOLD" and agreement:
            analysis.append(f"Final decision is {final_decision} because both signals align.")

        return analysis

    @staticmethod
    def _risk_level(volatility: float, disagreement: bool) -> str:
        if disagreement or volatility >= 0.03:
            return "high"
        if volatility >= 0.015:
            return "medium"
        return "low"
