"""Webhook actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import find_guild_webhook, parse_color, resolve_guild_channel
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


class EditWebhookInput(BaseModel):
    webhook_id: str
    name: str | None = Field(None, min_length=1, max_length=80)
    channel_id: str | None = None
    reason: str | None = Field(None, max_length=512)


async def edit_webhook_handler(ctx, data: EditWebhookInput):
    hook = await find_guild_webhook(ctx.guild, data.webhook_id)
    kwargs = {k: v for k, v in {"name": data.name, "reason": data.reason}.items() if v is not None}
    if data.channel_id:
        kwargs["channel"] = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not kwargs:
        raise ValueError("Provide a webhook name and/or channel_id.")
    await hook.edit(**kwargs)
    return {"webhook_id": data.webhook_id, "updated": True}


ActionRegistry.register(ActionDefinition(type="edit_webhook", description="Edits a webhook name or moves it to another channel.", input_schema=EditWebhookInput, required_bot_permissions=discord.Permissions(manage_webhooks=True), required_user_permissions=discord.Permissions(manage_webhooks=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=edit_webhook_handler))


class ExecuteWebhookInput(BaseModel):
    webhook_id: str
    content: str | None = Field(None, max_length=2000)
    embed_title: str | None = Field(None, max_length=256)
    embed_description: str | None = Field(None, max_length=4096)
    username: str | None = Field(None, max_length=80)
    avatar_url: str | None = Field(None, max_length=512)
    wait: bool = True


async def execute_webhook_handler(ctx, data: ExecuteWebhookInput):
    if not data.content and not data.embed_title and not data.embed_description:
        raise ValueError("Provide content or embed fields for the webhook message.")
    hook = await find_guild_webhook(ctx.guild, data.webhook_id)
    embed = None
    if data.embed_title or data.embed_description:
        embed = discord.Embed(title=data.embed_title, description=data.embed_description, color=parse_color(None) or discord.Color.blurple())
    result = await hook.send(content=data.content, embed=embed, username=data.username, avatar_url=data.avatar_url, wait=data.wait)
    return {"webhook_id": data.webhook_id, "sent": True, "message_id": str(result.id) if result else None}


ActionRegistry.register(ActionDefinition(type="execute_webhook", description="Executes a guild webhook with content or an embed. This can impersonate a webhook identity and always requires confirmation.", input_schema=ExecuteWebhookInput, required_bot_permissions=discord.Permissions(manage_webhooks=True), required_user_permissions=discord.Permissions(manage_webhooks=True), risk_level=RiskLevel.HIGH, confirmation_policy=ConfirmationPolicy.REQUIRED, handler=execute_webhook_handler))


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
