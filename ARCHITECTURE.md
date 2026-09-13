# Architecture Overview

```
User Prompt (Discord /prompt)
       ↓
Injection Defense & Sanitization
       ↓
Fallback / LLM Intent Parser (Google Gemini)
       ↓
Zod Schema Validation
       ↓
Action Registry Whitelist Check
       ↓
Tenant Guard & Guild Boundary Check
       ↓
Permission Engine & Role Hierarchy Analysis
       ↓
Guild Policy Engine
       ↓
Risk Assessment & Confirmation Gate
       ↓
Deterministic Dispatcher (Discord.js API)
       ↓
Audit Logging & Ephemeral / UI Response
```
