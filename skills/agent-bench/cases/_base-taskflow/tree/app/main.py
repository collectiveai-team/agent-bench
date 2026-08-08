import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.core.config import APP_VERSION, PREFECT_WORKER_MODE, Settings, get_settings
from app.db.session import create_database, init_db
from app.events import get_event_bus, poll_job_states
from app.routes import router
from app.services.dispatcher import drain_dispatch_tasks


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        settings_provider: Callable[[], Settings] = application.dependency_overrides.get(
            get_settings, get_settings
        )
        settings = settings_provider()
        engine, session_factory = create_database(settings.db_path)
        application.state.settings = settings
        application.state.engine = engine
        application.state.session_factory = session_factory
        await init_db(engine)
        poller_task: asyncio.Task[None] | None = None
        if settings.worker_mode == PREFECT_WORKER_MODE:
            poller_task = asyncio.create_task(
                poll_job_states(session_factory, application.state.bus)
            )
            application.state.status_poller_task = poller_task
        try:
            yield
        finally:
            try:
                if poller_task is not None:
                    poller_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await poller_task
                await drain_dispatch_tasks()
            finally:
                await engine.dispose()

    application = FastAPI(title="Taskflow", version=APP_VERSION, lifespan=lifespan)
    application.state.bus = get_event_bus()
    application.include_router(router)
    return application


app = create_app()
