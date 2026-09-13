# Security & Safety Invariants

1. **Deterministic Execution**: The LLM never touches Discord API client objects directly.
2. **Cryptographic Plan Hashing**: Confirmation requests serialize the action plan into a SHA-256 hash. If parameters are tampered with before button interaction, execution is blocked.
3. **Replay & Substitution Defense**: Nonces are single-use (`consumed: true`) and expire in 5 minutes.
4. **Prompt Injection Defense**: All user inputs and external Discord strings (e.g. channel topics) are sanitized and stripped of injection directives.
