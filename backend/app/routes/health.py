from fastapi import APIRouter

from app.utils.config import get_settings


settings = get_settings()
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
