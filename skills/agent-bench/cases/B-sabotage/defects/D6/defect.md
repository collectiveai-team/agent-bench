# D6 — Event published inside transaction; rollback still emits it

## Criterion violated

From the `L-taskflow` specification (WebSocket job event stream):
> Lifecycle events published by the service/worker persistence paths: `job.created` on POST.

Events must reflect durable state. Publishing before the DB commit means a transaction rollback produces a phantom `job.created` event for a job that was never persisted.

## Observable symptom

When `session.commit()` raises (e.g., a constraint violation), the `job.created` event has already been delivered to WebSocket subscribers. Subscribers see an event for a job that cannot be retrieved via `GET /jobs/{id}`.

## Hunt-list category

event published inside transaction — `event_bus.publish()` is called before `await session.commit()`, inverting the correct ordering (persist first, then notify).
