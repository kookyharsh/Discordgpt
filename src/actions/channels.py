"""Channel actions: create/delete/edit/rename/topic/slowmode/lock/move/permissions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

from typing import Literal

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_category, resolve_guild_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateChannelInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal["text", "voice", "category", "forum"] = "text"
    category_id: str | None = None
    topic: str | None = Field(None, max_length=1024)
    reason: str | None = Field(None, max_length=512)


async def create_channel_handler(ctx, input_data: CreateChannelInput):
    category = (
        await resolve_category(ctx.guild, input_data.category_id)
        if input_data.category_id
        else None
    )
    kwargs: dict = {"name": input_data.name}
    if input_data.reason:
        kwargs["reason"] = input_data.reason

    if input_data.type == "text":
        if input_data.topic:
            kwargs["topic"] = input_data.topic
        if category is not None:
            kwargs["category"] = category
        ch = await ctx.guild.create_text_channel(**kwargs)
    elif input_data.type == "voice":
        if category is not None:
            kwargs["category"] = category
        ch = await ctx.guild.create_voice_channel(**kwargs)
    elif input_data.type == "category":
        ch = await ctx.guild.create_category(**kwargs)
    elif input_data.type == "forum":
        if input_data.topic:
            kwargs["topic"] = input_data.topic
        if category is not None:
            kwargs["category"] = category
        ch = await ctx.guild.create_forum(**kwargs)
    else:  # pragma: no cover - pydantic Literal guards this
        raise ValueError(f"Unknown channel type: {input_data.type}")
    return {"channel_id": str(ch.id), "name": ch.name, "type": input_data.type}


ActionRegistry.register(
    ActionDefinition(
        type="create_channel",
        description="Creates a new text, voice, category, or forum channel.",
        input_schema=CreateChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_channel_handler,
    )
)


class DeleteChannelInput(BaseModel):
    channel_id: str
    reason: str | None = None


async def delete_channel_handler(ctx, input_data: DeleteChannelInput):
    ch = await resolve_guild_channel(ctx.guild, input_data.channel_id)
    name = getattr(ch, "name", str(ch.id))
    await ch.delete(reason=input_data.reason)
    return {"channel_id": input_data.channel_id, "name": name, "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_channel",
        description="Deletes a channel from the guild.",
        input_schema=DeleteChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.HIGH,
        confirmation_policy=ConfirmationPolicy.REQUIRED,
        handler=delete_channel_handler,
    )
)


class EditChannelInput(BaseModel):
    channel_id: str
    name: str | None = Field(None, max_length=100)
    topic: str | None = Field(None, max_length=1024)
    nsfw: bool | None = None
    reason: str | None = Field(None, max_length=512)


async def edit_channel_handler(ctx, input_data: EditChannelInput):
    ch = await resolve_guild_channel(ctx.guild, input_data.channel_id)
    kwargs: dict = {}
    if input_data.name:
        kwargs["name"] = input_data.name
    if input_data.topic is not None:
        if not isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
            raise ValueError("Only text and forum channels support a topic.")
        kwargs["topic"] = input_data.topic
    if input_data.nsfw is not None:
        if not hasattr(ch, "edit"):
            raise ValueError(f"Channel {input_data.channel_id} cannot be edited.")
        kwargs["nsfw"] = input_data.nsfw
    if input_data.reason:
        kwargs["reason"] = input_data.reason
    if not kwargs or (set(kwargs) == {"reason"}):
        raise ValueError("Nothing to change: provide name, topic, or nsfw.")
    await ch.edit(**kwargs)
    return {"channel_id": input_data.channel_id, "updated": True}


ActionRegistry.register(
    ActionDefinition(
        type="edit_channel",
        description="Edits properties of a channel such as name, topic, or nsfw flag.",
        input_schema=EditChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=edit_channel_handler,
    )
)


class RenameChannelInput(BaseModel):
    channel_id: str
    new_name: str = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=512)


async def rename_channel_handler(ctx, data: RenameChannelInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    await ch.edit(name=data.new_name, reason=data.reason)
    return {"channel_id": str(ch.id), "new_name": data.new_name}


ActionRegistry.register(
    ActionDefinition(
        type="rename_channel",
        description="Renames a channel.",
        input_schema=RenameChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=rename_channel_handler,
    )
)


class SetTopicInput(BaseModel):
    channel_id: str
    topic: str | None = Field(None, max_length=1024)
    reason: str | None = Field(None, max_length=512)


async def set_topic_handler(ctx, data: SetTopicInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
        raise ValueError(f"Topic-capable text channel {data.channel_id} not found.")
    topic = data.topic.strip() if data.topic and data.topic.strip() else None
    await ch.edit(topic=topic, reason=data.reason)
    return {"channel_id": str(ch.id), "topic": topic}


ActionRegistry.register(
    ActionDefinition(
        type="set_topic",
        description="Sets a text channel topic (empty clears it).",
        input_schema=SetTopicInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=set_topic_handler,
    )
)


class SetSlowmodeInput(BaseModel):
    channel_id: str
    seconds: int = Field(..., ge=0, le=21600)
    reason: str | None = Field(None, max_length=512)


async def set_slowmode_handler(ctx, data: SetSlowmodeInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.TextChannel):
        raise ValueError(f"Text channel {data.channel_id} not found.")
    await ch.edit(slowmode_delay=data.seconds, reason=data.reason)
    return {"channel_id": str(ch.id), "seconds": data.seconds}


ActionRegistry.register(
    ActionDefinition(
        type="set_slowmode",
        description="Sets slowmode delay in seconds on a text channel (0 disables).",
        input_schema=SetSlowmodeInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=set_slowmode_handler,
    )
)


class LockChannelInput(BaseModel):
    channel_id: str
    reason: str | None = Field(None, max_length=512)


async def lock_channel_handler(ctx, data: LockChannelInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    await ch.set_permissions(ctx.guild.default_role, send_messages=False, reason=data.reason)
    return {"channel_id": str(ch.id), "locked": True}


ActionRegistry.register(
    ActionDefinition(
        type="lock_channel",
        description="Locks a channel by denying Send Messages for @everyone.",
        input_schema=LockChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True, manage_roles=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=lock_channel_handler,
    )
)


class UnlockChannelInput(BaseModel):
    channel_id: str
    reason: str | None = Field(None, max_length=512)


async def unlock_channel_handler(ctx, data: UnlockChannelInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    await ch.set_permissions(ctx.guild.default_role, send_messages=None, reason=data.reason)
    return {"channel_id": str(ch.id), "locked": False}


ActionRegistry.register(
    ActionDefinition(
        type="unlock_channel",
        description="Unlocks a channel by resetting the @everyone Send Messages overwrite to neutral.",
        input_schema=UnlockChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True, manage_roles=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=unlock_channel_handler,
    )
)


class MoveChannelInput(BaseModel):
    channel_id: str
    position: int | None = Field(None, ge=0, le=500)
    category_id: str | None = None
    reason: str | None = Field(None, max_length=512)


async def move_channel_handler(ctx, data: MoveChannelInput):
    if data.position is None and not data.category_id:
        raise ValueError("Provide position and/or category_id to move the channel.")
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    kwargs: dict = {}
    if data.position is not None:
        kwargs["position"] = data.position
    if data.category_id:
        kwargs["category"] = await resolve_category(ctx.guild, data.category_id)
    if data.reason:
        kwargs["reason"] = data.reason
    await ch.edit(**kwargs)
    return {"channel_id": str(ch.id), "moved": True}


ActionRegistry.register(
    ActionDefinition(
        type="move_channel",
        description="Moves a channel to a new position and/or category.",
        input_schema=MoveChannelInput,
        required_bot_permissions=discord.Permissions(manage_channels=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=move_channel_handler,
    )
)


class SetChannelPermissionsInput(BaseModel):
    channel_id: str
    target_id: str = Field(..., description="Role or member ID for the overwrite")
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    reason: str | None = Field(None, max_length=512)


async def set_channel_permissions_handler(ctx, data: SetChannelPermissionsInput):
    from src.actions._helpers import coerce_snowflake

    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    target = None
    try:
        target = ctx.guild.get_role(coerce_snowflake(data.target_id, "role"))
    except ValueError:
        target = None
    if target is None:
        try:
            target = await resolve_member_by_id(ctx.guild, data.target_id)
        except ValueError:
            raise ValueError(f"Role or member {data.target_id} not found.") from None
    overwrite = discord.PermissionOverwrite()
    for perm in data.allow:
        if hasattr(discord.Permissions, perm):
            setattr(overwrite, perm, True)
    for perm in data.deny:
        if hasattr(discord.Permissions, perm):
            setattr(overwrite, perm, False)
    await ch.set_permissions(target, overwrite=overwrite, reason=data.reason)
    return {"channel_id": str(ch.id), "target_id": data.target_id, "updated": True}


async def resolve_member_by_id(guild: discord.Guild, member_id: str):
    from src.actions._helpers import resolve_member

    return await resolve_member(guild, member_id)


ActionRegistry.register(
    ActionDefinition(
        type="set_channel_permissions",
        description="Sets a permission overwrite for a role/member on a channel.",
        input_schema=SetChannelPermissionsInput,
        required_bot_permissions=discord.Permissions(manage_channels=True, manage_roles=True),
        required_user_permissions=discord.Permissions(manage_channels=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=set_channel_permissions_handler,
    )
)
