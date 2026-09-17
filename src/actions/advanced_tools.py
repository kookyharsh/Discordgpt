"""Advanced tools: threads, reactions, invites, voice moderation, message edit/delete.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateThreadInput(BaseModel):
    channel_id: str
    name: str = Field(..., min_length=1, max_length=100)
    message_id: str | None = None
    auto_archive_minutes: int | None = Field(None, ge=60, le=10080)
    reason: str | None = Field(None, max_length=512)


async def create_thread_handler(ctx, data: CreateThreadInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None or not isinstance(ch, discord.TextChannel):
        raise ValueError(f"Text channel {data.channel_id} not found.")
    kwargs: dict = {"name": data.name}
    if data.auto_archive_minutes is not None:
        kwargs["auto_archive_duration"] = data.auto_archive_minutes
    if data.reason is not None:
        kwargs["reason"] = data.reason
    if data.message_id:
        msg = await ch.fetch_message(int(data.message_id))
        thread = await msg.create_thread(**kwargs)
    else:
        thread = await ch.create_thread(**kwargs)
    return {"thread_id": str(thread.id), "name": thread.name}


ActionRegistry.register(
    ActionDefinition(
        type="create_thread",
        description="Creates a thread in a text channel, optionally attached to a message.",
        input_schema=CreateThreadInput,
        required_bot_permissions=discord.Permissions(
            send_messages=True, create_public_threads=True
        ),
        required_user_permissions=discord.Permissions(
            send_messages=True, create_public_threads=True
        ),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_thread_handler,
    )
)


class AddReactionInput(BaseModel):
    channel_id: str
    message_id: str
    emoji: str = Field(..., min_length=1, max_length=64)


async def add_reaction_handler(ctx, data: AddReactionInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Channel {data.channel_id} not found.")
    msg = await ch.fetch_message(int(data.message_id))
    await msg.add_reaction(data.emoji)
    return {"message_id": str(msg.id), "emoji": data.emoji, "reacted": True}


ActionRegistry.register(
    ActionDefinition(
        type="add_reaction",
        description="Adds an emoji reaction to a message.",
        input_schema=AddReactionInput,
        required_bot_permissions=discord.Permissions(add_reactions=True, read_message_history=True),
        required_user_permissions=discord.Permissions(add_reactions=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=add_reaction_handler,
    )
)


class CreateInviteInput(BaseModel):
    channel_id: str
    max_age: int = Field(0, ge=0, le=604800)
    max_uses: int = Field(0, ge=0, le=100)
    reason: str | None = Field(None, max_length=512)


async def create_invite_handler(ctx, data: CreateInviteInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Channel {data.channel_id} not found.")
    invite = await ch.create_invite(
        max_age=data.max_age, max_uses=data.max_uses or None, reason=data.reason
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


class MuteMemberInput(BaseModel):
    member_id: str
    muted: bool = True
    reason: str | None = Field(None, max_length=512)


async def mute_member_handler(ctx, data: MuteMemberInput):
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    await member.edit(mute=data.muted, reason=data.reason)
    return {"member_id": str(member.id), "muted": data.muted}


ActionRegistry.register(
    ActionDefinition(
        type="mute_member",
        description="Server-mutes or unmutes a member in voice.",
        input_schema=MuteMemberInput,
        required_bot_permissions=discord.Permissions(mute_members=True),
        required_user_permissions=discord.Permissions(mute_members=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=mute_member_handler,
    )
)


class DeafenMemberInput(BaseModel):
    member_id: str
    deafened: bool = True
    reason: str | None = Field(None, max_length=512)


async def deafen_member_handler(ctx, data: DeafenMemberInput):
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    await member.edit(deafen=data.deafened, reason=data.reason)
    return {"member_id": str(member.id), "deafened": data.deafened}


ActionRegistry.register(
    ActionDefinition(
        type="deafen_member",
        description="Server-deafens or undeafens a member in voice.",
        input_schema=DeafenMemberInput,
        required_bot_permissions=discord.Permissions(deafen_members=True),
        required_user_permissions=discord.Permissions(deafen_members=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=deafen_member_handler,
    )
)


class EditMessageInput(BaseModel):
    channel_id: str
    message_id: str
    content: str = Field(..., min_length=1, max_length=2000)


async def edit_message_handler(ctx, data: EditMessageInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Channel {data.channel_id} not found.")
    msg = await ch.fetch_message(int(data.message_id))
    if msg.author.id != ctx.guild.me.id:
        raise ValueError("Only the bot's own messages can be edited.")
    await msg.edit(content=data.content)
    return {"message_id": str(msg.id), "edited": True}


ActionRegistry.register(
    ActionDefinition(
        type="edit_message",
        description="Edits the content of a bot-sent message.",
        input_schema=EditMessageInput,
        required_bot_permissions=discord.Permissions(send_messages=True),
        required_user_permissions=discord.Permissions(send_messages=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=edit_message_handler,
    )
)


class DeleteMessageInput(BaseModel):
    channel_id: str
    message_id: str
    reason: str | None = Field(None, max_length=512)


async def delete_message_handler(ctx, data: DeleteMessageInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Channel {data.channel_id} not found.")
    msg = await ch.fetch_message(int(data.message_id))
    await msg.delete(reason=data.reason)
    return {"message_id": str(msg.id), "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_message",
        description="Deletes a single message by ID.",
        input_schema=DeleteMessageInput,
        required_bot_permissions=discord.Permissions(manage_messages=True),
        required_user_permissions=discord.Permissions(manage_messages=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=delete_message_handler,
    )
)
