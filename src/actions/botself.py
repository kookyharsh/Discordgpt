"""Bot-owned presence controls."""
from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import bot_client
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class SetPresenceInput(BaseModel):
    activity: str | None = Field(None, max_length=128)
    status: str = Field("online", pattern="^(online|idle|dnd|invisible|offline)$")

async def set_presence_handler(ctx, data: SetPresenceInput):
    client = bot_client(ctx)
    status = discord.Status.offline if data.status == "offline" else getattr(discord.Status, data.status)
    activity = discord.Game(name=data.activity) if data.activity else None
    await client.change_presence(activity=activity, status=status)
    return {"status": data.status, "activity": data.activity, "updated": True}

ActionRegistry.register(ActionDefinition(type="set_bot_presence", description="Sets the bot's Discord status and optional playing activity.", input_schema=SetPresenceInput, required_bot_permissions=discord.Permissions.none(), required_user_permissions=discord.Permissions.none(), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=set_presence_handler))
