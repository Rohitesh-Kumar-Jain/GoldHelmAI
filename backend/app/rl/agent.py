from __future__ import annotations

import pickle
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class QLearningTradingAgent:
    """Tabular Q-learning agent with discretized state buckets."""

    learning_rate: float = 0.12
    discount_factor: float = 0.92
    epsilon: float = 0.18
    epsilon_decay: float = 0.985
    min_epsilon: float = 0.03
    actions: tuple[int, int, int] = (0, 1, 2)
    q_table: dict[tuple[int, int, int], np.ndarray] = field(default_factory=dict)
    price_bins: np.ndarray | None = None
    ratio_bins: np.ndarray | None = None
    sentiment_bins: np.ndarray | None = None

    def fit_state_bins(self, states: np.ndarray) -> None:
        current_prices = states[:, 0]
        prediction_ratios = (states[:, 1] / np.maximum(states[:, 0], 1e-9)) - 1.0
        sentiments = states[:, 2]

        self.price_bins = np.quantile(current_prices, [0.2, 0.4, 0.6, 0.8])
        self.ratio_bins = np.array([-0.03, -0.01, 0.0, 0.01, 0.03])
        self.sentiment_bins = np.array([-0.35, -0.1, 0.1, 0.35])

    def choose_action(self, state: np.ndarray, explore: bool = True) -> int:
        state_key = self.discretize_state(state)
        self._ensure_state(state_key)

        if explore and random.random() < self.epsilon:
            return random.choice(self.actions)

        return int(np.argmax(self.q_table[state_key]))

    def update(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool) -> None:
        state_key = self.discretize_state(state)
        next_key = self.discretize_state(next_state)
        self._ensure_state(state_key)
        self._ensure_state(next_key)

        current_q = self.q_table[state_key][action]
        max_future_q = 0.0 if done else float(np.max(self.q_table[next_key]))
        updated_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_future_q - current_q
        )
        self.q_table[state_key][action] = updated_q

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def discretize_state(self, state: np.ndarray) -> tuple[int, int, int]:
        if self.price_bins is None or self.ratio_bins is None or self.sentiment_bins is None:
            raise ValueError("State bins have not been fitted.")

        current_price = float(state[0])
        prediction_ratio = (float(state[1]) / max(current_price, 1e-9)) - 1.0
        sentiment_score = float(state[2])

        price_bucket = int(np.digitize(current_price, self.price_bins))
        ratio_bucket = int(np.digitize(prediction_ratio, self.ratio_bins))
        sentiment_bucket = int(np.digitize(sentiment_score, self.sentiment_bins))
        return (price_bucket, ratio_bucket, sentiment_bucket)

    def q_values(self, state: np.ndarray) -> np.ndarray:
        state_key = self.discretize_state(state)
        self._ensure_state(state_key)
        return self.q_table[state_key]

    def save(self, path: str | Path, metadata: dict[str, float] | None = None) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump(
                {
                    "learning_rate": self.learning_rate,
                    "discount_factor": self.discount_factor,
                    "epsilon": self.epsilon,
                    "epsilon_decay": self.epsilon_decay,
                    "min_epsilon": self.min_epsilon,
                    "q_table": self.q_table,
                    "price_bins": self.price_bins,
                    "ratio_bins": self.ratio_bins,
                    "sentiment_bins": self.sentiment_bins,
                    "metadata": metadata or {},
                },
                handle,
            )

    @classmethod
    def load(cls, path: str | Path) -> tuple["QLearningTradingAgent", dict[str, float]]:
        with Path(path).open("rb") as handle:
            payload = pickle.load(handle)

        agent = cls(
            learning_rate=payload["learning_rate"],
            discount_factor=payload["discount_factor"],
            epsilon=payload["epsilon"],
            epsilon_decay=payload["epsilon_decay"],
            min_epsilon=payload["min_epsilon"],
        )
        agent.q_table = payload["q_table"]
        agent.price_bins = payload["price_bins"]
        agent.ratio_bins = payload["ratio_bins"]
        agent.sentiment_bins = payload["sentiment_bins"]
        return agent, payload.get("metadata", {})

    def _ensure_state(self, state_key: tuple[int, int, int]) -> None:
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(len(self.actions), dtype=float)
