import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.health import router as health_router
from app.routes.market import router as market_router
from app.utils.config import get_settings


settings = get_settings()
logging.basicConfig(
    level=logging.INFO if settings.app_env != "development" else logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="GoldHelm AI backend for gold price analysis and next-day prediction.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(market_router)
