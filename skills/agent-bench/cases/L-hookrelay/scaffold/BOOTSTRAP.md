# Hookrelay — scaffold bootstrap

Run the following commands from an empty directory to create the project scaffold and reach green gates before implementation begins.

## Step 1 — Initialise the project

```sh
uv init --name hookrelay --python 3.12
uv add fastapi uvicorn "sqlalchemy[asyncio]" aiosqlite pydantic-settings httpx
uv add --dev pytest pytest-asyncio ruff
mkdir -p app tests && touch app/__init__.py tests/__init__.py
```

`httpx` is a **runtime** dependency — it is the delivery client used by the dispatcher in production, not only a test utility.

## Step 2 — Add tool configuration to `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100
```

## Step 3 — Verify gates are green and tag the scaffold

```sh
uv run ruff check .
uv run pytest -q
git add -A && git commit -m "chore: bench scaffold" && git tag bench-base
```

Both gates must exit 0 before any implementation starts. An empty test suite is fine; if your `pytest` configuration treats "no tests collected" as a failure, add a trivial placeholder test.
