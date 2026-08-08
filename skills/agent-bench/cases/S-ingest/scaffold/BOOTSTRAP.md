# Ingest — scaffold bootstrap

Run the following commands from an empty directory to create the project
scaffold and reach green gates before implementation begins.

## Step 1 — Initialise the project

```sh
uv init --name ingest --python 3.12
uv add polars
uv add --dev pytest ruff
mkdir -p app tests && touch app/__init__.py tests/__init__.py
```

## Step 2 — Add tool configuration to `pyproject.toml`

```toml
[project.scripts]
ingest = "app.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

The `[project.scripts]` entry makes `uv run ingest` available from the project
root. The `[tool.hatch.build.targets.wheel]` entry tells hatchling where to find
the package (the default hatchling heuristic looks for a directory matching the
project name; because the project is `ingest` but the code is in `app/`, this
explicit declaration is required). The target module and function
(`app.cli:main`) are a scaffold suggestion; you may reorganise freely as long as
`uv run ingest` works correctly.

## Step 3 — Verify gates are green and tag the scaffold

```sh
uv run ruff check .
uv run pytest -q
git add -A && git commit -m "chore: bench scaffold" && git tag bench-base
```

Both gates must exit 0 before any implementation starts. An empty test suite
is fine; if your `pytest` configuration treats "no tests collected" as a
failure, add a trivial placeholder test.
