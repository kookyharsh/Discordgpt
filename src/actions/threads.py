"""Thread actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

from typing import Literal

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel, resolve_thread
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateThreadInput(BaseModel):
    channel_id: str
    name: str = Field(..., min_length=1, max_length=100)
    message_id: str | None = None
    auto_archive_minutes: Literal[60, 1440, 4320, 10080] | None = None
    reason: str | None = Field(None, max_length=512)


async def create_thread_handler(ctx, data: CreateThreadInput):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.TextChannel):
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


class ThreadStateInput(BaseModel):
    thread_id: str


async def join_thread_handler(ctx, data: ThreadStateInput):
    thread = await resolve_thread(ctx.guild, data.thread_id)
    await thread.join()
    return {"thread_id": data.thread_id, "joined": True}


async def leave_thread_handler(ctx, data: ThreadStateInput):
    thread = await resolve_thread(ctx.guild, data.thread_id)
    await thread.leave()
    return {"thread_id": data.thread_id, "left": True}


for _name, _handler, _description in (
    ("join_thread", join_thread_handler, "Joins a thread as the bot."),
    ("leave_thread", leave_thread_handler, "Leaves a thread as the bot."),
):
    ActionRegistry.register(
        ActionDefinition(
            type=_name,
            description=_description,
            input_schema=ThreadStateInput,
            required_bot_permissions=discord.Permissions(send_messages=True),
            required_user_permissions=discord.Permissions(send_messages=True),
            risk_level=RiskLevel.LOW,
            confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
            handler=_handler,
        )
    )


class ListArchivedThreadsInput(BaseModel):
    channel_id: str
    limit: int = Field(25, ge=1, le=100)


async def list_archived_threads_handler(ctx, data: ListArchivedThreadsInput):
    channel = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not hasattr(channel, "archived_threads"):
        raise ValueError("Channel does not support archived thread listing.")
    result = []
    async for thread in channel.archived_threads(limit=data.limit):
        result.append({"thread_id": str(thread.id), "name": thread.name, "archived": thread.archived})
    return {"threads": result}


ActionRegistry.register(
    ActionDefinition(
        type="list_archived_threads",
        description="Lists archived threads under a text, announcement, forum, or media channel.",
        input_schema=ListArchivedThreadsInput,
        required_bot_permissions=discord.Permissions(read_message_history=True),
        required_user_permissions=discord.Permissions(read_message_history=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_archived_threads_handler,
    )
)


class ArchiveThreadInput(BaseModel):
    thread_id: str
    archived: bool = True
    reason: str | None = Field(None, max_length=512)


async def archive_thread_handler(ctx, data: ArchiveThreadInput):
    thread = ctx.guild.get_thread(int(data.thread_id))
    if thread is None:
        thread = await resolve_guild_channel(ctx.guild, data.thread_id)
    if not isinstance(thread, discord.Thread):
        raise ValueError(f"Thread {data.thread_id} not found.")
    await thread.edit(archived=data.archived, reason=data.reason)
    return {"thread_id": str(thread.id), "archived": data.archived}


ActionRegistry.register(
    ActionDefinition(
        type="archive_thread",
        description="Archives or unarchives a thread.",
        input_schema=ArchiveThreadInput,
        required_bot_permissions=discord.Permissions(manage_threads=True),
        required_user_permissions=discord.Permissions(manage_threads=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=archive_thread_handler,
    )
)


class ListActiveThreadsInput(BaseModel):
    pass


async def list_active_threads_handler(ctx, data: ListActiveThreadsInput):
    threads = list(ctx.guild.threads)
    try:
        active = await ctx.guild.active_threads()
        threads = list(active)
    except Exception:
        pass
    return {
        "threads": [
            {"thread_id": str(t.id), "name": t.name, "archived": t.archived} for t in threads[:25]
        ]
    }


ActionRegistry.register(
    ActionDefinition(
        type="list_active_threads",
        description="Lists active threads in the guild.",
        input_schema=ListActiveThreadsInput,
        required_bot_permissions=discord.Permissions(read_message_history=True),
        required_user_permissions=discord.Permissions(read_message_history=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_active_threads_handler,
    )
)
