from __future__ import annotations

import numpy as np
import pandas as pd

from app.rl.agent import QLearningTradingAgent
from app.rl.environment import TradingEnvironment
from app.services.data_service import GoldDataService
from app.services.feature_service import FeatureEngineeringService
from app.services.news_service import NewsService
from app.services.sentiment_service import SentimentService
from app.utils.config import get_settings


def build_training_frame() -> pd.DataFrame:
    data_service = GoldDataService()
    news_service = NewsService()
    sentiment_service = SentimentService()
    feature_service = FeatureEngineeringService()

    raw = data_service.get_training_frame()
    articles = news_service.get_latest_news()
    sentiment_series = sentiment_service.build_daily_sentiment_series(
        articles,
        pd.to_datetime(raw["date"], errors="coerce"),
    )
    features = feature_service.build_features(raw, sentiment_series=sentiment_series)

    prior_signal = features["target_return"].shift(1).rolling(5, min_periods=1).mean().fillna(0.0)
    synthetic_prediction_return = np.clip(
        prior_signal + features["sentiment_score"] * 0.08,
        -0.05,
        0.05,
    )

    training_frame = pd.DataFrame(
        {
            "current_price": features["close"],
            "prediction": features["close"] * (1.0 + synthetic_prediction_return),
            "sentiment_score": features["sentiment_score"],
            "next_price": features["close"] * (1.0 + features["target_return"]),
        }
    )
    return training_frame.reset_index(drop=True)


def train_agent(episodes: int | None = None) -> dict[str, float]:
    settings = get_settings()
    episode_count = episodes or settings.rl_training_episodes
    training_frame = build_training_frame()
    environment = TradingEnvironment(training_frame, initial_cash=settings.rl_initial_cash)

    states = training_frame[["current_price", "prediction", "sentiment_score"]].to_numpy(dtype=float)
    agent = QLearningTradingAgent()
    agent.fit_state_bins(states)

    for _ in range(episode_count):
        state = environment.reset()
        done = False
        while not done:
            action = agent.choose_action(state, explore=True)
            result = environment.step(action)
            agent.update(state, action, result.reward, result.next_state, result.done)
            state = result.next_state
            done = result.done
        agent.decay_epsilon()

    metrics = environment.evaluate_policy(lambda state: agent.choose_action(state, explore=False))
    metrics["episodes"] = float(episode_count)
    agent.save(settings.rl_model_path, metadata=metrics)
    return metrics


if __name__ == "__main__":
    results = train_agent()
    print(results)
