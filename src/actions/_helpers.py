"""Shared helpers for category action modules."""

from __future__ import annotations

import re

import discord

_BRACKETED_ID_RE = re.compile(r"^<#(\d{15,25})>$")
_BRACKETED_USER_RE = re.compile(r"^<@!?(\d{15,25})>$")
_BRACKETED_ROLE_RE = re.compile(r"^<@&(\d{15,25})>$")
_BRACKETED_EMOJI_RE = re.compile(r"^<a?:\w+:(\d{15,25})>$")


def coerce_snowflake(value: str, kind: str) -> int:
    """Accept bare IDs and mention forms (`<#id>`, `<@id>`, `<@&id>`, `<:n:id>`)."""
    text = str(value or "").strip()
    for pattern in (
        _BRACKETED_ID_RE,
        _BRACKETED_USER_RE,
        _BRACKETED_ROLE_RE,
        _BRACKETED_EMOJI_RE,
    ):
        m = pattern.match(text)
        if m:
            return int(m.group(1))
    try:
        return int(text)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {kind} ID: {value!r}.") from None


async def resolve_guild_channel(guild: discord.Guild, channel_id: str):
    """Return any guild channel by ID (cache then REST)."""
    channel_id_int = coerce_snowflake(channel_id, "channel")
    ch = guild.get_channel(channel_id_int)
    if ch is not None:
        return ch
    try:
        ch = await guild.fetch_channel(channel_id_int)
    except discord.NotFound:
        raise ValueError(f"Channel {channel_id} not found.") from None
    except discord.HTTPException as e:
        raise ValueError(f"Could not fetch channel {channel_id}: {e}") from e
    if ch is None:
        raise ValueError(f"Channel {channel_id} not found.")
    return ch


async def resolve_text_channel(guild: discord.Guild, channel_id: str):
    """Return a text-capable channel or raise a friendly ValueError."""
    ch = await resolve_guild_channel(guild, channel_id)
    if isinstance(ch, discord.CategoryChannel):
        raise ValueError(f"Channel {channel_id} is a category, not a message channel.")
    if not hasattr(ch, "fetch_message"):
        raise ValueError(f"Channel {channel_id} cannot contain messages.")
    return ch


async def resolve_member(guild: discord.Guild, member_id: str):
    """Resolve a member by ID, mention, or username/nickname (needs members intent)."""
    text = str(member_id or "").strip()
    if re.fullmatch(r"\d{15,25}", text):
        member = guild.get_member(int(text))
        if member is not None:
            return member
        try:
            return await guild.fetch_member(int(text))
        except discord.NotFound:
            raise ValueError(f"Member {member_id} not found.") from None
        except discord.HTTPException as e:
            raise ValueError(f"Could not fetch member {member_id}: {e}") from e
    # Names (or bracketed mentions) go through the full resolver.
    from src.entities.entity_resolver import EntityResolver

    res = await EntityResolver.resolve_member(guild, text)
    if res.resolved is not None:
        return res.resolved
    if res.ambiguous and res.matches:
        options = ", ".join(str(getattr(m, "display_name", m)) for m in res.matches[:5])
        raise ValueError(
            f"Multiple members match '{member_id}': {options}. @mention the user instead."
        )
    raise ValueError(
        f"Member '{member_id}' not found. @mention the user or use their ID "
        "(name search only finds current server members)."
    )


async def resolve_category(guild: discord.Guild, category_id: str | None):
    """Return a CategoryChannel or None. Raises if the ID is not a category."""
    if not category_id:
        return None
    ch = await resolve_guild_channel(guild, category_id)
    if not isinstance(ch, discord.CategoryChannel):
        raise ValueError(f"Category {category_id} not found or is not a category.")
    return ch
