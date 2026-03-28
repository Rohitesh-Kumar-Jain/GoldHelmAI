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


class PredictResponse(BaseModel):
    ticker: str
    as_of: date
    prediction: float
    predicted_change_pct: float
    confidence: float
    model: str
    validation_mae: float
    sentiment: SentimentPayload
    explanation: list[str]
