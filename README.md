# Discord Natural Language Agent (Python)

Production-grade, multi-tenant Discord management bot with native Needle tool-calling. Users describe operations in natural language (`/prompt`); the bot translates them into whitelisted, permission-checked Discord actions.

> The bot lives in [`bot-py/`](bot-py/). This repo is Python-only; the old TypeScript implementation was removed (see git history).

## Quick start

```powershell
cd bot-py
Copy-Item .env.example .env
# edit .env: set DISCORD_TOKEN
docker-compose up -d --build
```

In Discord: `/prompt request:create channel welcome`

## Layout

- `bot-py/` — the bot (`discord.py`, `cactus-needle`, `SQLAlchemy`, `APScheduler`, `FastAPI`)
- `bot-py/README.md` — full run/test docs
- `docs/TOOL_CATALOG.md` — whitelisted action catalog (31 tools)
- `tools/discord_tools.json` — generated Needle schemas
- `needle/` — vendored Needle reference (untracked)

## Safety invariants

1. No code execution — Needle is planner-only.
2. Every action whitelisted in `ActionRegistry` with strict Pydantic schemas.
3. Tenant isolation by `guildId`, confirmation gate for HIGH/CRITICAL ops, full audit logging.
