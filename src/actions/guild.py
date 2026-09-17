"""Guild actions: info/edit/bans.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class GetGuildInfoInput(BaseModel):
    pass


async def get_guild_info_handler(ctx, data: GetGuildInfoInput):
    guild = ctx.guild
    return {
        "guild_id": str(guild.id),
        "name": guild.name,
        "member_count": guild.member_count,
        "channel_count": len(guild.channels),
        "role_count": len(guild.roles),
        "owner_id": str(guild.owner_id) if guild.owner_id else None,
        "description": guild.description,
    }


ActionRegistry.register(
    ActionDefinition(
        type="get_guild_info",
        description="Returns basic guild info: name, member/channel/role counts.",
        input_schema=GetGuildInfoInput,
        required_bot_permissions=discord.Permissions.none(),
        required_user_permissions=discord.Permissions.none(),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=get_guild_info_handler,
    )
)


class EditGuildInput(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    reason: str | None = Field(None, max_length=512)


async def edit_guild_handler(ctx, data: EditGuildInput):
    if data.name is None and data.description is None:
        raise ValueError("Provide name and/or description to update.")
    kwargs: dict = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.description is not None:
        kwargs["description"] = data.description
    if data.reason:
        kwargs["reason"] = data.reason
    guild = await ctx.guild.edit(**kwargs)
    return {"guild_id": str(guild.id), "name": guild.name}


ActionRegistry.register(
    ActionDefinition(
        type="edit_guild",
        description="Edits guild name and/or description.",
        input_schema=EditGuildInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=edit_guild_handler,
    )
)


class ListBansInput(BaseModel):
    limit: int = Field(50, ge=1, le=200)


async def list_bans_handler(ctx, data: ListBansInput):
    entries = []
    count = 0
    async for ban in ctx.guild.bans(limit=data.limit):
        entries.append({"user_id": str(ban.user.id), "user": str(ban.user)})
        count += 1
        if count >= data.limit:
            break
    return {"bans": entries}


ActionRegistry.register(
    ActionDefinition(
        type="list_bans",
        description="Lists banned users in the guild.",
        input_schema=ListBansInput,
        required_bot_permissions=discord.Permissions(ban_members=True),
        required_user_permissions=discord.Permissions(ban_members=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_bans_handler,
    )
)
