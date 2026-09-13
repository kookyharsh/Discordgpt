# DiscordGPT Architecture

## Overview
DiscordGPT is a production-grade, public, multi-tenant Discord management agent that allows server administrators to describe desired Discord operations in natural language.

## Design Philosophy & Authority Boundary
- **LLM as Planner/Parser only**: The LLM interprets natural language into structured JSON action plans matching strict Zod schemas. It never receives raw Discord client references or executes code.
- **Application as Authority**: The TypeScript application enforces action whitelisting, permission checks, Discord role hierarchy constraints, policy evaluation, and single-use cryptographic confirmations.
- **Discord as Enforcement Boundary**: Live API endpoints validate final action parameters and permissions.

## Execution Pipeline
```
Natural Language Prompt
    ↓
Natural Language Parser (Deterministic Stage 1 + LLM Stage 2)
    ↓
Zod Intent Schema Validation
    ↓
Action Registry Whitelist Check
    ↓
Guild Policy & Rate Limit Evaluation
    ↓
Permission Engine & Discord Hierarchy Check
    ↓
Risk Classification (LOW / MEDIUM / HIGH / CRITICAL)
    ↓
Confirmation Manager (Plan Hashing & Nonce Expiration if High Risk)
    ↓
Deterministic ActionDispatcher
    ↓
DiscordAdapter Layer (Live Discord.js / Mock Adapter)
    ↓
Tenant-Scoped Audit Log
```
