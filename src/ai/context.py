"""Compact guild context for the Needle engine.

The engine has a ~256-token sliding window shared by system facts, the
top-5 retrieved tools, and the prompt. The previous builder flattened up
to 6x300-char history lines into `system` (history alone could evict the
system facts) and threw away the channel/role name lists entirely, so the
model guessed names that don't exist.

This builder emits names (not snowflakes - EntityResolver maps names to
IDs, including the disambiguation flow) under a token budget, truncating
lowest-priority facts first: history -> roles -> channels.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Rough token estimate for short English text (the engine uses its own
# tokenizer; len/4 is a conservative upper bound for budgeting).
MAX_SYSTEM_TOKENS = 150
MAX_CHANNELS = 25
MAX_ROLES = 10
MAX_HISTORY_TURNS = 3
HISTORY_CHARS = 100


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _names(items: list[Any], limit: int) -> list[str]:
    seen: list[str] = []
    for item in items[:limit]:
        name = str(getattr(item, "name", "") or "").strip()
        if name and name.lower() not in {s.lower() for s in seen}:
            seen.append(name)
    return seen


def build_system(
    guild,
    current_channel_id: str | None = None,
    history: list[str] | None = None,
    now: datetime | None = None,
    max_tokens: int = MAX_SYSTEM_TOKENS,
    people: dict[str, str] | None = None,
) -> str:
    """Build a compact `system` fact string for a single parse turn.

    `people` maps mentioned user IDs to display labels, e.g.
    {"123": "@Bob"}, so the model can emit IDs directly.
    """
    from datetime import UTC

    now = now or datetime.now(UTC)
    parts: list[str] = [f"date: {now.strftime('%Y-%m-%d %a %H:%M')}", "locale: en-US"]

    channels: list[str] = []
    roles: list[str] = []
    current_name: str | None = None
    try:
        guild_channels = list(getattr(guild, "channels", []) or [])
    except Exception:
        guild_channels = []
    try:
        guild_roles = list(getattr(guild, "roles", []) or [])
    except Exception:
        guild_roles = []

    # Current channel first so it survives truncation.
    if current_channel_id:
        for ch in guild_channels:
            if str(getattr(ch, "id", "")) == str(current_channel_id):
                current_name = str(getattr(ch, "name", "") or "")
                break
    if current_name:
        parts.append(f"here: #{current_name}")

    channels = [
        c for c in _names(guild_channels, MAX_CHANNELS) if c.lower() != (current_name or "").lower()
    ]
    if current_name:
        channels = [current_name, *channels][:MAX_CHANNELS]
    roles = _names(guild_roles, MAX_ROLES)
    try:
        member_count = getattr(guild, "member_count", None)
    except Exception:
        member_count = None
    if people:
        who = ",".join(f"{label}={uid}" for uid, label in list(people.items())[:5])
        if who:
            parts.append(f"people: {who}")

    turns: list[str] = []
    for line in (history or [])[-MAX_HISTORY_TURNS:]:
        text = str(line).strip().replace("\n", " ")
        if text:
            turns.append(text[:HISTORY_CHARS])

    # Assemble under budget, dropping lowest priority first.
    def assemble(n_channels: int, n_roles: int, n_turns: int) -> str:
        segs = list(parts)
        if n_channels and channels:
            shown = channels[:n_channels]
            extra = len(channels) - len(shown)
            segs.append(
                "channels: "
                + ",".join(f"#{c}" for c in shown)
                + (f",+{extra}more" if extra else "")
            )
        if n_roles and roles:
            segs.append("roles: " + ",".join(f"@{r}" for r in roles[:n_roles]))
        if member_count:
            segs.append(f"members: {member_count}")
        for t in turns[-n_turns:] if n_turns else []:
            segs.append(f"prev: {t}")
        return "; ".join(segs)

    n_ch, n_ro, n_tu = len(channels), len(roles), len(turns)
    while True:
        text = assemble(n_ch, n_ro, n_tu)
        if estimate_tokens(text) <= max_tokens:
            return text
        if n_tu:
            n_tu -= 1
        elif n_ro:
            n_ro -= 1
        elif n_ch > 5:
            n_ch -= 1
        else:
            return text
