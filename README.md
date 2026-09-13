# DiscordGPT

Production-grade, public, multi-tenant Discord bot that allows users to describe desired Discord operations in natural language.

## Architecture & Security Principles
1. **LLM as Planner/Parser only**: Zero raw Discord.js client access or execution capability given to LLM outputs.
2. **Zero Code Execution**: Dynamic `eval()`, `Function()`, Python execution, shell execution, or script execution are strictly prohibited.
3. **Application Authority**: All natural language inputs are converted to structured JSON plans and validated through a central `ActionRegistry`, `PermissionEngine`, and `PolicyEngine`.
4. **Single-Use Confirmation**: Dangerous operations (kicks, bans, deletions) require explicit single-use cryptographic plan confirmations.
5. **Multi-Tenant Scoping**: All operations, audit logs, saved commands, and schedules are strictly bound to `guildId`.

## Requirements
- Node.js 22+
- pnpm
- Docker & Docker Compose (for Postgres & Redis)

## Local Development
```bash
# Install dependencies
pnpm install

# Build TypeScript
pnpm run build

# Run unit & security tests
pnpm test

# Run dev mode
pnpm run dev
```

## Supported LLM Providers
- OpenAI (`LLM_PROVIDER=openai`)
- Gemini (`LLM_PROVIDER=gemini`)
- Claude (`LLM_PROVIDER=claude`)
- Mock (`LLM_PROVIDER=mock`)
