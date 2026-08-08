from fastapi import APIRouter

from app.core.config import APP_VERSION
from app.routes.jobs import router as jobs_router
from app.routes.stats import router as stats_router
from app.routes.ws import router as ws_router

router = APIRouter()
router.include_router(jobs_router)
router.include_router(stats_router)
router.include_router(ws_router)


@router.get("/")
async def root() -> dict[str, str]:
    return {"service": "taskflow", "version": APP_VERSION}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
