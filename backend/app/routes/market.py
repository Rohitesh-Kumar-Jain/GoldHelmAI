import logging

from fastapi import APIRouter, HTTPException

from app.agents.reasoning_agent import ReasoningAgent
from app.models.schemas import (
    HistoryResponse,
    PredictResponse,
    PriceResponse,
    SentimentResponse,
)
from app.rl.inference import RLInferenceService
from app.services.data_service import DataUnavailableError, GoldDataService
from app.services.news_service import NewsService
from app.services.prediction_service import PredictionService
from app.services.indicator_service import IndicatorService
from app.services.sentiment_service import SentimentService
from app.utils.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


router = APIRouter(prefix=f"{settings.api_prefix}/api" if settings.api_prefix else "/api", tags=["market"])

data_service = GoldDataService()
news_service = NewsService()
sentiment_service = SentimentService()
reasoning_agent = ReasoningAgent()
rl_inference_service = RLInferenceService()
indicator_service = IndicatorService()
prediction_service = PredictionService(
    data_service=data_service,
    news_service=news_service,
    sentiment_service=sentiment_service,
    reasoning_agent=reasoning_agent,
    rl_inference_service=rl_inference_service,
    indicator_service=indicator_service,
)


@router.get("/price", response_model=PriceResponse)
def get_latest_price() -> PriceResponse:
    try:
        latest = data_service.get_latest_price()
        return PriceResponse(**latest)
    except DataUnavailableError as exc:
        logger.exception("Failed to load latest market price.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/history", response_model=HistoryResponse)
def get_history() -> HistoryResponse:
    try:
        history = data_service.get_price_history()
        return HistoryResponse(ticker=data_service.ticker, history=history)
    except DataUnavailableError as exc:
        logger.exception("Failed to load market history.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/sentiment", response_model=SentimentResponse)
def get_sentiment() -> SentimentResponse:
    sentiment = prediction_service.get_latest_sentiment()
    return SentimentResponse(**sentiment)


@router.get("/predict", response_model=PredictResponse)
def get_prediction() -> PredictResponse:
    try:
        prediction_payload = prediction_service.predict_next_day()
        if prediction_payload is None:
            raise HTTPException(
                status_code=503,
                detail="Not enough market history is available to generate a prediction.",
            )
        return PredictResponse(**prediction_payload)
    except DataUnavailableError as exc:
        logger.exception("Failed to generate market prediction.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
