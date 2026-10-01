"""Stage instance lifecycle actions."""
from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class StartStageInput(BaseModel):
    channel_id: str
    topic: str = Field(..., min_length=1, max_length=120)
    send_start_notification: bool = False
async def start_stage_handler(ctx, data):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.StageChannel): raise ValueError("Stage actions require a stage channel.")
    instance = await ch.create_instance(topic=data.topic, send_start_notification=data.send_start_notification)
    return {"stage_id": str(instance.id), "channel_id": data.channel_id, "topic": instance.topic}
ActionRegistry.register(ActionDefinition(type="start_stage", description="Starts a moderated Stage instance in a stage channel for an AMA, talk, or live event.", input_schema=StartStageInput, required_bot_permissions=discord.Permissions(manage_channels=True), required_user_permissions=discord.Permissions(manage_channels=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=start_stage_handler))

class EditStageInput(BaseModel):
    channel_id: str
    topic: str = Field(..., min_length=1, max_length=120)
async def edit_stage_handler(ctx, data):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    instance = await ch.fetch_instance()
    await instance.edit(topic=data.topic)
    return {"channel_id": data.channel_id, "topic": data.topic, "updated": True}
ActionRegistry.register(ActionDefinition(type="edit_stage", description="Updates the topic of the active Stage instance in a channel.", input_schema=EditStageInput, required_bot_permissions=discord.Permissions(manage_channels=True), required_user_permissions=discord.Permissions(manage_channels=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=edit_stage_handler))

class EndStageInput(BaseModel):
    channel_id: str
async def end_stage_handler(ctx, data):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    instance = await ch.fetch_instance()
    await instance.delete()
    return {"channel_id": data.channel_id, "ended": True}
ActionRegistry.register(ActionDefinition(type="end_stage", description="Ends the active Stage instance in a stage channel.", input_schema=EndStageInput, required_bot_permissions=discord.Permissions(manage_channels=True), required_user_permissions=discord.Permissions(manage_channels=True), risk_level=RiskLevel.HIGH, confirmation_policy=ConfirmationPolicy.REQUIRED, handler=end_stage_handler))
