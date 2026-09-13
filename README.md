# Discord Natural Language Agent

A production-grade, multi-tenant Discord management bot that allows users to describe desired Discord operations in natural language.

## Key Principles & Invariants

1. **No Code Execution**: The bot NEVER executes arbitrary code (`eval`, `Function()`, `vm`, `child_process`, or shell commands).
2. **LLM as Planner Only**: The LLM is strictly an intent parser and planner. The application enforces authorization and execution deterministically.
3. **Whitelisted Operations**: Every supported action is explicitly registered in the Action Registry with strict Zod schemas.
4. **Tenant Isolation**: Every database record, audit log, and execution context is strictly scoped by `guildId`.
5. **Confirmation & Safety**: Dangerous or destructive operations (e.g. banning members, deleting channels) require explicit user confirmation using single-use, time-bound Discord UI buttons backed by cryptographic plan hashing.

## Quick Start (Docker)

```bash
# 1. Copy environment example
cp .env.example .env

# 2. Run with Docker Compose
docker-compose up -d --build
```

## Documentation Index

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and flow
- [SECURITY.md](./SECURITY.md) - Security model and threat mitigation
- [PERMISSIONS.md](./PERMISSIONS.md) - Permission engine & Discord role hierarchy
- [ACTIONS.md](./ACTIONS.md) - Supported Discord action catalog
- [SCHEDULER.md](./SCHEDULER.md) - BullMQ job scheduler & safety
- [DATABASE.md](./DATABASE.md) - PostgreSQL schema and Prisma setup
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Production deployment guidelines
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Guide for adding new actions and features
