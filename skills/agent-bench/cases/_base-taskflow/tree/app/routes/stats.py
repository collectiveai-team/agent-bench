from fastapi import APIRouter

from app.routes.jobs import JobServiceDependency
from app.schemas import StatsResponse

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(service: JobServiceDependency):
    return await service.stats()
