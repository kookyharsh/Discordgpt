"""Scheduled event actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

from datetime import datetime

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateScheduledEventInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    start_time: datetime
    description: str | None = Field(None, max_length=1000)
    channel_id: str | None = None
    end_time: datetime | None = None
    reason: str | None = Field(None, max_length=512)


async def create_scheduled_event_handler(ctx, data: CreateScheduledEventInput):
    kwargs: dict = {
        "name": data.name,
        "start_time": data.start_time,
        "privacy_level": discord.PrivacyLevel.guild_only,
    }
    if data.channel_id:
        ch = await resolve_guild_channel(ctx.guild, data.channel_id)
        kwargs["channel"] = ch
        kwargs["entity_type"] = discord.EntityType.voice
    else:
        kwargs["entity_type"] = discord.EntityType.external
        kwargs["location"] = "Discord"
    if data.description:
        kwargs["description"] = data.description
    if data.end_time:
        kwargs["end_time"] = data.end_time
    if data.reason:
        kwargs["reason"] = data.reason
    event = await ctx.guild.create_scheduled_event(**kwargs)
    return {"event_id": str(event.id), "name": event.name}


ActionRegistry.register(
    ActionDefinition(
        type="create_scheduled_event",
        description="Creates a scheduled event (voice if channel_id given, else external).",
        input_schema=CreateScheduledEventInput,
        required_bot_permissions=discord.Permissions(manage_events=True),
        required_user_permissions=discord.Permissions(manage_events=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_scheduled_event_handler,
    )
)


class ListScheduledEventsInput(BaseModel):
    pass


async def list_scheduled_events_handler(ctx, data: ListScheduledEventsInput):
    events = await ctx.guild.fetch_scheduled_events()
    return {
        "events": [
            {"event_id": str(e.id), "name": e.name, "status": str(e.status)} for e in events[:25]
        ]
    }


ActionRegistry.register(
    ActionDefinition(
        type="list_scheduled_events",
        description="Lists scheduled events in the guild.",
        input_schema=ListScheduledEventsInput,
        required_bot_permissions=discord.Permissions(manage_events=True),
        required_user_permissions=discord.Permissions(manage_events=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_scheduled_events_handler,
    )
)


class DeleteScheduledEventInput(BaseModel):
    event_id: str


async def delete_scheduled_event_handler(ctx, data: DeleteScheduledEventInput):
    event = await ctx.guild.fetch_scheduled_event(int(data.event_id))
    await event.delete()
    return {"event_id": data.event_id, "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_scheduled_event",
        description="Deletes a scheduled event by ID.",
        input_schema=DeleteScheduledEventInput,
        required_bot_permissions=discord.Permissions(manage_events=True),
        required_user_permissions=discord.Permissions(manage_events=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=delete_scheduled_event_handler,
    )
)
