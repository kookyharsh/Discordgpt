"""Message actions: send/edit/delete/pin/purge/react/history.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel, resolve_text_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class SendMessageInput(BaseModel):
    channel_id: str
    content: str = Field(..., min_length=1, max_length=2000)


async def send_message_handler(ctx, input_data: SendMessageInput):
    ch = await resolve_text_channel(ctx.guild, input_data.channel_id)
    if not hasattr(ch, "send"):
        raise ValueError(f"Channel {input_data.channel_id} cannot receive messages.")
    msg = await ch.send(content=input_data.content)
    return {"message_id": str(msg.id), "channel_id": str(ch.id), "sent": True}


ActionRegistry.register(
    ActionDefinition(
        type="send_message",
        description="Sends a text message to a channel.",
        input_schema=SendMessageInput,
        required_bot_permissions=discord.Permissions(send_messages=True),
        required_user_permissions=discord.Permissions(send_messages=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=send_message_handler,
    )
)


class EditMessageInput(BaseModel):
    channel_id: str
    message_id: str
    content: str = Field(..., min_length=1, max_length=2000)


async def edit_message_handler(ctx, data: EditMessageInput):
    ch = await resolve_text_channel(ctx.guild, data.channel_id)
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


async def delete_message_handler(ctx, data: DeleteMessageInput):
    ch = await resolve_text_channel(ctx.guild, data.channel_id)
    msg = await ch.fetch_message(int(data.message_id))
    await msg.delete()
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


async def _fetch_message(ctx, channel_id: str, message_id: str):
    ch = await resolve_text_channel(ctx.guild, channel_id)
    return await ch.fetch_message(int(message_id))


class PinMessageInput(BaseModel):
    channel_id: str
    message_id: str
    reason: str | None = Field(None, max_length=512)


async def pin_message_handler(ctx, data: PinMessageInput):
    msg = await _fetch_message(ctx, data.channel_id, data.message_id)
    if msg.pinned:
        return {"message_id": str(msg.id), "pinned": True, "note": "Already pinned."}
    await msg.pin(reason=data.reason)
    return {"message_id": str(msg.id), "pinned": True}


ActionRegistry.register(
    ActionDefinition(
        type="pin_message",
        description="Pins a message in a text channel.",
        input_schema=PinMessageInput,
        required_bot_permissions=discord.Permissions(manage_messages=True),
        required_user_permissions=discord.Permissions(manage_messages=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=pin_message_handler,
    )
)


class UnpinMessageInput(BaseModel):
    channel_id: str
    message_id: str
    reason: str | None = Field(None, max_length=512)


async def unpin_message_handler(ctx, data: UnpinMessageInput):
    msg = await _fetch_message(ctx, data.channel_id, data.message_id)
    if not msg.pinned:
        return {"message_id": str(msg.id), "unpinned": True, "note": "Not pinned."}
    await msg.unpin(reason=data.reason)
    return {"message_id": str(msg.id), "unpinned": True}


ActionRegistry.register(
    ActionDefinition(
        type="unpin_message",
        description="Unpins a message in a text channel.",
        input_schema=UnpinMessageInput,
        required_bot_permissions=discord.Permissions(manage_messages=True),
        required_user_permissions=discord.Permissions(manage_messages=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=unpin_message_handler,
    )
)


class PurgeMessagesInput(BaseModel):
    channel_id: str
    limit: int = Field(..., ge=1, le=100)
    user_id: str | None = None
    reason: str | None = Field(None, max_length=512)


async def purge_messages_handler(ctx, data: PurgeMessagesInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.TextChannel):
        raise ValueError(f"Purgeable text channel {data.channel_id} not found.")

    def _check(m: discord.Message) -> bool:
        if m.pinned:
            return False
        return not (data.user_id and str(m.author.id) != data.user_id)

    deleted = await ch.purge(limit=data.limit, check=_check, reason=data.reason)
    return {"channel_id": str(ch.id), "deleted": len(deleted)}


ActionRegistry.register(
    ActionDefinition(
        type="purge_messages",
        description="Bulk-deletes recent messages (max 100, skips pinned and older-than-14d).",
        input_schema=PurgeMessagesInput,
        required_bot_permissions=discord.Permissions(manage_messages=True),
        required_user_permissions=discord.Permissions(manage_messages=True),
        risk_level=RiskLevel.HIGH,
        confirmation_policy=ConfirmationPolicy.REQUIRED,
        handler=purge_messages_handler,
    )
)


class AddReactionInput(BaseModel):
    channel_id: str
    message_id: str
    emoji: str = Field(..., min_length=1, max_length=64)


async def add_reaction_handler(ctx, data: AddReactionInput):
    ch = await resolve_text_channel(ctx.guild, data.channel_id)
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


class FetchHistoryInput(BaseModel):
    channel_id: str
    limit: int = Field(10, ge=1, le=50)


async def fetch_history_handler(ctx, data: FetchHistoryInput):
    ch = await resolve_text_channel(ctx.guild, data.channel_id)
    messages = []
    async for msg in ch.history(limit=data.limit):
        messages.append(
            {
                "message_id": str(msg.id),
                "author": str(msg.author),
                "content": msg.content[:500],
                "created_at": msg.created_at.isoformat(),
            }
        )
    return {"channel_id": str(ch.id), "messages": messages}


ActionRegistry.register(
    ActionDefinition(
        type="fetch_history",
        description="Reads recent message history from a channel (up to 50).",
        input_schema=FetchHistoryInput,
        required_bot_permissions=discord.Permissions(read_message_history=True),
        required_user_permissions=discord.Permissions(read_message_history=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=fetch_history_handler,
    )
)


class ClearReactionsInput(BaseModel):
    channel_id: str
    message_id: str


async def clear_reactions_handler(ctx, data: ClearReactionsInput):
    ch = await resolve_text_channel(ctx.guild, data.channel_id)
    msg = await ch.fetch_message(int(data.message_id))
    await msg.clear_reactions()
    return {"message_id": str(msg.id), "cleared": True}


ActionRegistry.register(
    ActionDefinition(
        type="clear_reactions",
        description="Removes all reactions from a message.",
        input_schema=ClearReactionsInput,
        required_bot_permissions=discord.Permissions(manage_messages=True),
        required_user_permissions=discord.Permissions(manage_messages=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=clear_reactions_handler,
    )
)
