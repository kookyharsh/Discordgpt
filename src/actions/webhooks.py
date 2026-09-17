"""Webhook actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateWebhookInput(BaseModel):
    channel_id: str
    name: str = Field(..., min_length=1, max_length=80)
    reason: str | None = Field(None, max_length=512)


async def create_webhook_handler(ctx, data: CreateWebhookInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.TextChannel):
        raise ValueError(f"Text channel {data.channel_id} not found.")
    hook = await ch.create_webhook(name=data.name, reason=data.reason)
    return {"webhook_id": str(hook.id), "url": hook.url}


ActionRegistry.register(
    ActionDefinition(
        type="create_webhook",
        description="Creates a webhook in a text channel.",
        input_schema=CreateWebhookInput,
        required_bot_permissions=discord.Permissions(manage_webhooks=True),
        required_user_permissions=discord.Permissions(manage_webhooks=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_webhook_handler,
    )
)


class ListWebhooksInput(BaseModel):
    pass


async def list_webhooks_handler(ctx, data: ListWebhooksInput):
    hooks = await ctx.guild.webhooks()
    return {
        "webhooks": [
            {"webhook_id": str(h.id), "name": h.name, "channel_id": str(h.channel_id)}
            for h in hooks[:25]
        ]
    }


ActionRegistry.register(
    ActionDefinition(
        type="list_webhooks",
        description="Lists webhooks in the guild.",
        input_schema=ListWebhooksInput,
        required_bot_permissions=discord.Permissions(manage_webhooks=True),
        required_user_permissions=discord.Permissions(manage_webhooks=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_webhooks_handler,
    )
)


class DeleteWebhookInput(BaseModel):
    webhook_id: str


async def delete_webhook_handler(ctx, data: DeleteWebhookInput):
    for hook in await ctx.guild.webhooks():
        if str(hook.id) == data.webhook_id:
            await hook.delete()
            return {"webhook_id": data.webhook_id, "deleted": True}
    raise ValueError(f"Webhook {data.webhook_id} not found.")


ActionRegistry.register(
    ActionDefinition(
        type="delete_webhook",
        description="Deletes a webhook by ID.",
        input_schema=DeleteWebhookInput,
        required_bot_permissions=discord.Permissions(manage_webhooks=True),
        required_user_permissions=discord.Permissions(manage_webhooks=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=delete_webhook_handler,
    )
)
