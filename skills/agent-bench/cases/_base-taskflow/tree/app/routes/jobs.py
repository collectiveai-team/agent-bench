from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEFAULT_JOB_LIMIT, DEFAULT_JOB_OFFSET
from app.db.session import get_session
from app.schemas import JobCreate, JobListResponse, JobResponse
from app.services.jobs import (
    InvalidJobListQueryError,
    JobNotFoundError,
    JobRunningError,
    JobService,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobService:
    return JobService(
        session, request.app.state.settings, event_bus=request.app.state.bus
    )


JobServiceDependency = Annotated[JobService, Depends(get_job_service)]


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_create: JobCreate, service: JobServiceDependency):
    return await service.create(job_create)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    service: JobServiceDependency,
    job_status: Annotated[str | None, Query(alias="status")] = None,
    limit: int = DEFAULT_JOB_LIMIT,
    offset: int = DEFAULT_JOB_OFFSET,
):
    try:
        jobs, total = await service.list(job_status, limit, offset)
    except InvalidJobListQueryError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"jobs": jobs, "total": total}


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, service: JobServiceDependency):
    try:
        return await service.get(job_id)
    except JobNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, service: JobServiceDependency) -> Response:
    try:
        await service.delete(job_id)
    except JobNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except JobRunningError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
