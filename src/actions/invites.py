"""Invite actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateInviteInput(BaseModel):
    channel_id: str
    max_age: int = Field(0, ge=0, le=604800)
    max_uses: int = Field(0, ge=0, le=100)
    reason: str | None = Field(None, max_length=512)


async def create_invite_handler(ctx, data: CreateInviteInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    invite = await ch.create_invite(
        max_age=data.max_age, max_uses=data.max_uses, reason=data.reason
    )
    return {"code": invite.code, "url": invite.url}


ActionRegistry.register(
    ActionDefinition(
        type="create_invite",
        description="Creates a server invite for a channel (max_age/max_uses 0 = unlimited).",
        input_schema=CreateInviteInput,
        required_bot_permissions=discord.Permissions(create_instant_invite=True),
        required_user_permissions=discord.Permissions(create_instant_invite=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_invite_handler,
    )
)


class ListInvitesInput(BaseModel):
    pass


async def list_invites_handler(ctx, data: ListInvitesInput):
    invites = await ctx.guild.invites()
    return {
        "invites": [
            {"code": i.code, "url": i.url, "uses": i.uses, "max_uses": i.max_uses}
            for i in invites[:25]
        ]
    }


ActionRegistry.register(
    ActionDefinition(
        type="list_invites",
        description="Lists active server invites.",
        input_schema=ListInvitesInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_invites_handler,
    )
)


class DeleteInviteInput(BaseModel):
    code: str = Field(..., min_length=2, max_length=32)


async def delete_invite_handler(ctx, data: DeleteInviteInput):
    invite = await ctx.bot.fetch_invite(data.code) if hasattr(ctx, "bot") else None
    if invite is None:
        # Fall back: find in guild invites then delete.
        for inv in await ctx.guild.invites():
            if inv.code == data.code:
                await inv.delete()
                return {"code": data.code, "deleted": True}
        raise ValueError(f"Invite {data.code} not found.")
    await invite.delete()
    return {"code": data.code, "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_invite",
        description="Deletes a server invite by code.",
        input_schema=DeleteInviteInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=delete_invite_handler,
    )
)
