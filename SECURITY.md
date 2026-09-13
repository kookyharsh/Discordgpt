# DiscordGPT Security Model

## Zero Arbitrary Code Execution Policy
DiscordGPT strictly forbids dynamic code execution:
- No `eval()`
- No `Function()`
- No `child_process` or `shell` execution
- No dynamic JavaScript / Python script generation
- No raw tool execution by LLM

## Multi-Tenant Isolation
All database records (Audit logs, Saved Commands, Schedules, Executions, Settings) are strictly scoped by `guildId`. Cross-guild resource manipulation is prevented via `TenantGuard`.

## Confirmation & Replay Protection
- High-risk actions require explicit confirmation.
- Confirmation payloads contain cryptographic SHA-256 plan hashes.
- Confirmations expire after 5 minutes and are single-use nonces.

## Role Hierarchy & Permissions
- Requesting user permissions and bot permissions are independently checked against Discord API state.
- Discord's role hierarchy is enforced to prevent privilege escalation attempts.
