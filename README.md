# Discord Agent (Python - discord.py & Cactus-Needle)

A production-grade, multi-tenant Discord management agent written in Python using `discord.py@2.x` and `cactus-needle` for native LLM tool-calling.

## Architecture & Features

- **Native Needle Tool-Calling**: Every Discord operation is registered as a `@needle.tool` function with Pydantic type signatures and bounds.
- **SQLAlchemy + AsyncPG**: Direct 1:1 mapping onto existing PostgreSQL schemas with `guild_id` tenant isolation on every repository operation.
- **Strict Execution Dispatcher**: Deterministic Python execution engine enforcing tenant isolation, role hierarchy, bot permissions, and server policy before executing mutations.
- **Single-Use UI Confirmations**: High/Critical risk operations require single-use Discord UI component confirmation (Buttons & Select Menus) backed by SHA-256 plan hashes expiring in 5 minutes.
- **FastAPI Endpoint**: Exposes `/health`, `/ready`, and `/metrics` for system monitoring.
- **APScheduler**: Asynchronous background task scheduler re-evaluating full permission & policy stacks prior to execution.

## Quick Start (Docker)

```bash
# Copy environment settings
cp .env.example .env
# edit .env: set DISCORD_TOKEN

# Run stack with docker-compose
docker-compose up -d --build
```

In Discord: `/prompt request:create channel welcome`

> **Name search needs one portal toggle:** in the Discord developer portal
> (your app → Bot), enable **Server Members Intent**. Without it, `@mentions`
> and IDs still work, but typing plain names (`timeout Bob`) can't resolve.

## Local Dev (uv)

```bash
uv venv
uv sync --extra dev
cp .env.example .env
uv run python -m src.main
```

## Running Tests

```bash
uv run pytest tests -q
```

## Layout

- `src/` — bot source (`bot/`, `actions/`, `ai/`, `database/`, `scheduler/`, `security/`)
- `tests/` — pytest suite
- `docs/TOOL_CATALOG.md` — whitelisted action catalog (31 tools)
- `tools/discord_tools.json` — generated Needle schemas
