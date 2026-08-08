import asyncio
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import WS_CONNECTED_EVENT
from app.events import Event, EventBus

router = APIRouter()


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


@router.websocket("/ws/jobs")
async def stream_jobs(websocket: WebSocket, job_id: str | None = None) -> None:
    bus: EventBus = websocket.app.state.bus
    queue = bus.subscribe()
    disconnect_task: asyncio.Task[None] | None = None
    event_task: asyncio.Task[Event] | None = None
    try:
        await websocket.accept()
        await websocket.send_json({"event": WS_CONNECTED_EVENT})
        disconnect_task = asyncio.create_task(_wait_for_disconnect(websocket))

        while True:
            event_task = asyncio.create_task(queue.get())
            completed, _ = await asyncio.wait(
                {disconnect_task, event_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if disconnect_task in completed:
                await disconnect_task
                break

            event = event_task.result()
            event_task = None
            if job_id is None or event.get("job_id") == job_id:
                await websocket.send_json(event)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        for task in (disconnect_task, event_task):
            if task is not None and not task.done():
                task.cancel()
            if task is not None:
                with suppress(asyncio.CancelledError, Exception):
                    await task
        bus.unsubscribe(queue)
