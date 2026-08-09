# D1 — Datetime timezone lost across persistence round-trip

## Criterion violated

From the `L-taskflow` specification (Application skeleton and SQLite persistence):
> `created_at` / `started_at` / `finished_at` (UTC datetimes, only `created_at` non-null at insert).

UTC datetimes must carry timezone information through the full request/response cycle, including after a DB round-trip.

## Observable symptom

`GET /jobs/{id}` returns `created_at` as a naive datetime string (e.g. `"2026-01-01T12:00:00.000000"`) — no `Z` suffix, no UTC offset. The original `POST /jobs` response matches because the column default also produces a naive datetime, hiding the loss at first glance.

A caller that relies on `datetime.fromisoformat(created_at).tzinfo` receives `None` instead of `UTC`.

## Hunt-list category

naive/aware datetime loss — `UTCDateTime` TypeDecorator replaced with plain `DateTime()` on the `created_at` column; the TypeDecorator's `process_result_value` (which re-attaches UTC on load from SQLite) is no longer called.
