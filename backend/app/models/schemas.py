from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PriceResponse(BaseModel):
    ticker: str
    date: date
    price: float


class HistoryItem(BaseModel):
    date: date
    close: float


class HistoryResponse(BaseModel):
    ticker: str
    history: list[HistoryItem]


class NewsItem(BaseModel):
    title: str
    description: str
    published_at: str


class SentimentPayload(BaseModel):
    score: float
    label: str


class SentimentResponse(BaseModel):
    score: float
    label: str
    article_count: int
    articles: list[NewsItem]
    updated_at: str


class DebateAgent(BaseModel):
    decision: str
    confidence: float


class BacktestPayload(BaseModel):
    total_return: float
    number_of_trades: float
    win_rate: float
    final_portfolio_value: float


class DebatePayload(BaseModel):
    reasoning_agent: DebateAgent
    rl_agent: DebateAgent
    policy_source: str
    agreement: bool


class PredictResponse(BaseModel):
    ticker: str
    as_of: date
    current_price: float
    prediction: float
    decision: str
    rl_decision: str
    predicted_change_pct: float
    confidence: float
    model: str
    validation_mae: float
    sentiment: SentimentPayload
    debate: DebatePayload
    backtest: BacktestPayload
    final_analysis: list[str]
    analysis: list[str]
