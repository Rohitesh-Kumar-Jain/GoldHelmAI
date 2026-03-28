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
        portfolio_history = [self.initial_cash]
        step_returns: list[float] = []

        while not done:
            action = int(policy_fn(state))
            step_result = self.step(action)
            state = step_result.next_state
            done = step_result.done
            last_value = step_result.info["portfolio_value"]
            portfolio_history.append(last_value)
            previous_value = portfolio_history[-2]
            step_returns.append((last_value - previous_value) / max(previous_value, 1e-9))

        total_return = (last_value - self.initial_cash) / self.initial_cash
        win_rate = self.win_count / self.trade_count if self.trade_count else 0.0
        sharpe_ratio = self._sharpe_ratio(step_returns)
        max_drawdown = self._max_drawdown(portfolio_history)
        return {
            "total_return": round(float(total_return), 4),
            "number_of_trades": float(self.trade_count),
            "win_rate": round(float(win_rate), 4),
            "final_portfolio_value": round(float(last_value), 2),
            "sharpe_ratio": round(float(sharpe_ratio), 4),
            "max_drawdown": round(float(max_drawdown), 4),
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

    @staticmethod
    def _sharpe_ratio(step_returns: list[float]) -> float:
        if len(step_returns) < 2:
            return 0.0

        returns = np.array(step_returns, dtype=float)
        volatility = float(np.std(returns))
        if volatility == 0:
            return 0.0
        return float(np.mean(returns) / volatility * np.sqrt(len(returns)))

    @staticmethod
    def _max_drawdown(portfolio_history: list[float]) -> float:
        if not portfolio_history:
            return 0.0

        values = np.array(portfolio_history, dtype=float)
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / np.maximum(running_max, 1e-9)
        return abs(float(np.min(drawdowns)))
