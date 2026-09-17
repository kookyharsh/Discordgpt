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
cd bot-py

# Copy environment settings
cp .env.example .env

# Run stack with docker-compose
docker-compose up -d --build
```

## Running Tests

```bash
cd bot-py
pytest
```
