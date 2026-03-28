from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class StepResult:
    next_state: np.ndarray
    reward: float
    done: bool
    info: dict[str, float]


class TradingEnvironment:
    """A lightweight trading simulator with cash, holdings, and mark-to-market rewards."""

    HOLD = 0
    BUY = 1
    SELL = 2

    def __init__(
        self,
        frame: pd.DataFrame,
        initial_cash: float = 10_000.0,
        unit_size: float = 1.0,
    ) -> None:
        self.frame = frame.reset_index(drop=True).copy()
        self.initial_cash = initial_cash
        self.unit_size = unit_size
        self.current_step = 0
        self.cash = initial_cash
        self.holdings = 0.0
        self.trade_count = 0
        self.win_count = 0

    def reset(self) -> np.ndarray:
        self.current_step = 0
        self.cash = self.initial_cash
        self.holdings = 0.0
        self.trade_count = 0
        self.win_count = 0
        return self._get_state(self.current_step)

    def step(self, action: int) -> StepResult:
        row = self.frame.iloc[self.current_step]
        current_price = float(row["current_price"])
        next_price = float(row["next_price"])
        previous_value = self._portfolio_value(current_price)

        if action == self.BUY and self.cash >= current_price * self.unit_size:
            self.cash -= current_price * self.unit_size
            self.holdings += self.unit_size
            self.trade_count += 1
        elif action == self.SELL and self.holdings >= self.unit_size:
            self.cash += current_price * self.unit_size
            self.holdings -= self.unit_size
            self.trade_count += 1

        current_value = self._portfolio_value(next_price)
        reward = current_value - previous_value
        if action in (self.BUY, self.SELL) and reward > 0:
            self.win_count += 1

        self.current_step += 1
        done = self.current_step >= len(self.frame)
        next_state = (
            self._get_state(self.current_step)
            if not done
            else np.array([current_price, row["prediction"], row["sentiment_score"]], dtype=float)
        )

        return StepResult(
            next_state=next_state,
            reward=float(reward),
            done=done,
            info={"portfolio_value": current_value},
        )

    def evaluate_policy(self, policy_fn) -> dict[str, float]:
        state = self.reset()
        done = False
        last_value = self.initial_cash

        while not done:
            action = int(policy_fn(state))
            step_result = self.step(action)
            state = step_result.next_state
            done = step_result.done
            last_value = step_result.info["portfolio_value"]

        total_return = (last_value - self.initial_cash) / self.initial_cash
        win_rate = self.win_count / self.trade_count if self.trade_count else 0.0
        return {
            "total_return": round(float(total_return), 4),
            "number_of_trades": float(self.trade_count),
            "win_rate": round(float(win_rate), 4),
            "final_portfolio_value": round(float(last_value), 2),
        }

    def _get_state(self, step: int) -> np.ndarray:
        row = self.frame.iloc[step]
        return np.array(
            [
                float(row["current_price"]),
                float(row["prediction"]),
                float(row["sentiment_score"]),
            ],
            dtype=float,
        )

    def _portfolio_value(self, price: float) -> float:
        return float(self.cash + self.holdings * price)
