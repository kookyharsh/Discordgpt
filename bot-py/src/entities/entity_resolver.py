from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Generic, TypeVar

import discord

T = TypeVar("T")


@dataclass
class ResolutionResult(Generic[T]):
    resolved: T | None = None
    matches: list[T] | None = None
    ambiguous: bool = False
    not_found: bool = False


class EntityResolver:
    @staticmethod
    async def resolve_channel(
        guild: discord.Guild, query: str
    ) -> ResolutionResult[discord.abc.GuildChannel]:
        cleaned = query.lstrip("#").strip().lower()
        # Snowflake direct hit
        if re.fullmatch(r"\d{15,25}", cleaned):
            ch = guild.get_channel(int(cleaned))
            if ch is not None:
                return ResolutionResult(resolved=ch)
            try:
                ch = await guild.fetch_channel(int(cleaned))
                if ch is not None:
                    return ResolutionResult(resolved=ch)
            except Exception:
                pass

        exact = [c for c in guild.channels if c.name.lower() == cleaned]
        if len(exact) == 1:
            return ResolutionResult(resolved=exact[0])
        if len(exact) > 1:
            return ResolutionResult(matches=exact, ambiguous=True)

        partial = [c for c in guild.channels if cleaned in c.name.lower()]
        if len(partial) == 1:
            return ResolutionResult(resolved=partial[0])
        if len(partial) > 1:
            return ResolutionResult(matches=partial, ambiguous=True)
        return ResolutionResult(not_found=True)

    @staticmethod
    async def resolve_role(guild: discord.Guild, query: str) -> ResolutionResult[discord.Role]:
        cleaned = query.lstrip("@").strip().lower()
        if re.fullmatch(r"\d{15,25}", cleaned):
            role = guild.get_role(int(cleaned))
            if role is not None:
                return ResolutionResult(resolved=role)
            return ResolutionResult(not_found=True)

        exact = [r for r in guild.roles if r.name.lower() == cleaned]
        if len(exact) == 1:
            return ResolutionResult(resolved=exact[0])
        if len(exact) > 1:
            return ResolutionResult(matches=exact, ambiguous=True)

        partial = [r for r in guild.roles if cleaned in r.name.lower()]
        if len(partial) == 1:
            return ResolutionResult(resolved=partial[0])
        if len(partial) > 1:
            return ResolutionResult(matches=partial, ambiguous=True)
        return ResolutionResult(not_found=True)

    @staticmethod
    async def resolve_member(guild: discord.Guild, query: str) -> ResolutionResult[discord.Member]:
        # ID or mention lookup via single REST fetch. Full search requires
        # privileged members intent, so username search is unsupported.
        mention = re.match(r"^<@!?(\d+)>$", query.strip())
        candidate = mention.group(1) if mention else query.lstrip("@").strip()
        if re.fullmatch(r"\d{15,25}", candidate):
            member = guild.get_member(int(candidate))
            if member is not None:
                return ResolutionResult(resolved=member)
            try:
                member = await guild.fetch_member(int(candidate))
                if member is not None:
                    return ResolutionResult(resolved=member)
            except Exception:
                pass
        return ResolutionResult(not_found=True)
