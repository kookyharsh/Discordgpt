"""Parity tools: the remaining actions from the original 23-action catalog.

Imported for side effects (ActionRegistry.register). Imported by main.py
alongside needle_tools.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel
from src.permissions.permission_engine import HierarchyEngine

# ---------- members ----------


class KickMemberInput(BaseModel):
    member_id: str
    reason: str | None = Field(None, max_length=512)


async def kick_member_handler(ctx, data: KickMemberInput):
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    ok, reason = HierarchyEngine.can_bot_manage_member(ctx.guild, member)
    if not ok:
        raise ValueError(reason)
    await member.kick(reason=data.reason)
    return {"member_id": str(member.id), "kicked": True}


ActionRegistry.register(
    ActionDefinition(
        type="kick_member",
        description="Kicks a member from the guild (they can rejoin with a new invite).",
        input_schema=KickMemberInput,
        required_bot_permissions=discord.Permissions(kick_members=True),
        required_user_permissions=discord.Permissions(kick_members=True),
        risk_level=RiskLevel.HIGH,
        confirmation_policy=ConfirmationPolicy.REQUIRED,
        handler=kick_member_handler,
    )
)


class UnbanMemberInput(BaseModel):
    user_id: str
    reason: str | None = Field(None, max_length=512)


async def unban_member_handler(ctx, data: UnbanMemberInput):
    await ctx.guild.unban(user=discord.Object(id=int(data.user_id)), reason=data.reason)
    return {"user_id": data.user_id, "unbanned": True}


ActionRegistry.register(
    ActionDefinition(
        type="unban_member",
        description="Unbans a user by ID so they can rejoin the guild.",
        input_schema=UnbanMemberInput,
        required_bot_permissions=discord.Permissions(ban_members=True),
        required_user_permissions=discord.Permissions(ban_members=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=unban_member_handler,
    )
)


class UntimeoutMemberInput(BaseModel):
    member_id: str
    reason: str | None = Field(None, max_length=512)


async def untimeout_member_handler(ctx, data: UntimeoutMemberInput):
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    if member.timed_out_until is None:
        return {
            "member_id": str(member.id),
            "untimed_out": False,
            "note": "Member is not timed out.",
        }
    await member.timeout(None, reason=data.reason)
    return {"member_id": str(member.id), "untimed_out": True}


ActionRegistry.register(
    ActionDefinition(
        type="untimeout_member",
        description="Removes an active timeout from a member.",
        input_schema=UntimeoutMemberInput,
        required_bot_permissions=discord.Permissions(moderate_members=True),
        required_user_permissions=discord.Permissions(moderate_members=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=untimeout_member_handler,
    )
)


class SetNicknameInput(BaseModel):
    member_id: str
    nickname: str | None = Field(None, max_length=32)
    reason: str | None = Field(None, max_length=512)


async def set_nickname_handler(ctx, data: SetNicknameInput):
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    ok, reason = HierarchyEngine.can_bot_manage_member(ctx.guild, member)
    if not ok:
        raise ValueError(reason)
    nick = data.nickname.strip() if data.nickname and data.nickname.strip() else None
    await member.edit(nick=nick, reason=data.reason)
    return {"member_id": str(member.id), "nickname": nick}


ActionRegistry.register(
    ActionDefinition(
        type="set_nickname",
        description="Sets or clears a member nickname (empty nickname clears it).",
        input_schema=SetNicknameInput,
        required_bot_permissions=discord.Permissions(manage_nicknames=True),
        required_user_permissions=discord.Permissions(manage_nicknames=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=set_nickname_handler,
    )
)


class MoveMemberInput(BaseModel):
    member_id: str
    channel_id: str | None = None
    reason: str | None = Field(None, max_length=512)


async def move_member_handler(ctx, data: MoveMemberInput):
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    if member.voice is None or member.voice.channel is None:
        raise ValueError(f"{member} is not in a voice channel.")
    if data.channel_id:
        target = ctx.guild.get_channel(int(data.channel_id))
        if target is None or not isinstance(target, discord.VoiceChannel):
            raise ValueError(f"Voice channel {data.channel_id} not found.")
        await member.move_to(target, reason=data.reason)
    else:
        await member.move_to(None, reason=data.reason)
    return {"member_id": str(member.id), "channel_id": data.channel_id, "moved": True}


ActionRegistry.register(
    ActionDefinition(
        type="move_member",
        description="Moves a member to a voice channel, or disconnects them when no channel is given.",
        input_schema=MoveMemberInput,
        required_bot_permissions=discord.Permissions(move_members=True),
        required_user_permissions=discord.Permissions(move_members=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=move_member_handler,
    )
)

# ---------- roles ----------


class DeleteRoleInput(BaseModel):
    role_id: str
    reason: str | None = Field(None, max_length=512)


async def delete_role_handler(ctx, data: DeleteRoleInput):
    role = ctx.guild.get_role(int(data.role_id))
    if role is None:
        raise ValueError(f"Role {data.role_id} not found.")
    ok, reason = HierarchyEngine.can_bot_manage_role(ctx.guild, role)
    if not ok:
        raise ValueError(reason)
    name = role.name
    await role.delete(reason=data.reason)
    return {"role_id": data.role_id, "name": name, "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_role",
        description="Deletes a role from the guild.",
        input_schema=DeleteRoleInput,
        required_bot_permissions=discord.Permissions(manage_roles=True),
        required_user_permissions=discord.Permissions(manage_roles=True),
        risk_level=RiskLevel.HIGH,
        confirmation_policy=ConfirmationPolicy.REQUIRED,
        handler=delete_role_handler,
    )
)


class RemoveRoleInput(BaseModel):
    member_id: str
    role_id: str


async def remove_role_handler(ctx, data: RemoveRoleInput):
    role = ctx.guild.get_role(int(data.role_id))
    if role is None:
        raise ValueError(f"Role {data.role_id} not found.")
    member = ctx.guild.get_member(int(data.member_id)) or await ctx.guild.fetch_member(
        int(data.member_id)
    )
    if role not in member.roles:
        return {
            "member_id": str(member.id),
            "role_id": str(role.id),
            "removed": False,
            "note": "Member does not have this role.",
        }
    await member.remove_roles(role)
    return {"member_id": str(member.id), "role_id": str(role.id), "removed": True}


ActionRegistry.register(
    ActionDefinition(
        type="remove_role",
        description="Removes a role from a guild member.",
        input_schema=RemoveRoleInput,
        required_bot_permissions=discord.Permissions(manage_roles=True),
        required_user_permissions=discord.Permissions(manage_roles=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=remove_role_handler,
    )
)


class EditRoleInput(BaseModel):
    role_id: str
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = None
    hoist: bool | None = None
    mentionable: bool | None = None
    reason: str | None = Field(None, max_length=512)


async def edit_role_handler(ctx, data: EditRoleInput):
    if all(v is None for v in (data.name, data.color, data.hoist, data.mentionable)):
        raise ValueError(
            "Nothing to change: provide at least one of name, color, hoist, mentionable."
        )
    role = ctx.guild.get_role(int(data.role_id))
    if role is None:
        raise ValueError(f"Role {data.role_id} not found.")
    ok, reason = HierarchyEngine.can_bot_manage_role(ctx.guild, role)
    if not ok:
        raise ValueError(reason)
    kwargs: dict = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.color is not None:
        try:
            kwargs["colour"] = discord.Color(int(data.color.replace("#", ""), 16))
        except ValueError:
            pass
    if data.hoist is not None:
        kwargs["hoist"] = data.hoist
    if data.mentionable is not None:
        kwargs["mentionable"] = data.mentionable
    if data.reason is not None:
        kwargs["reason"] = data.reason
    updated = await role.edit(**kwargs)
    return {"role_id": str(updated.id), "name": updated.name}


ActionRegistry.register(
    ActionDefinition(
        type="edit_role",
        description="Edits a role name, color, hoist, or mentionable flag.",
        input_schema=EditRoleInput,
        required_bot_permissions=discord.Permissions(manage_roles=True),
        required_user_permissions=discord.Permissions(manage_roles=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=edit_role_handler,
    )
)

# ---------- messages ----------


class PinMessageInput(BaseModel):
    channel_id: str
    message_id: str
    reason: str | None = Field(None, max_length=512)


async def _fetch_message(ctx, channel_id: str, message_id: str):
    ch = ctx.guild.get_channel(int(channel_id))
    if ch is None:
        raise ValueError(f"Text channel {channel_id} not found.")
    return await ch.fetch_message(int(message_id))


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
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None or not isinstance(ch, discord.TextChannel):
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

# ---------- channels (parity extras) ----------


class SetSlowmodeInput(BaseModel):
    channel_id: str
    seconds: int = Field(..., ge=0, le=21600)
    reason: str | None = Field(None, max_length=512)


async def set_slowmode_handler(ctx, data: SetSlowmodeInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None or not isinstance(ch, discord.TextChannel):
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
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Guild channel {data.channel_id} not found.")
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
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Guild channel {data.channel_id} not found.")
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


class RenameChannelInput(BaseModel):
    channel_id: str
    new_name: str = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=512)


async def rename_channel_handler(ctx, data: RenameChannelInput):
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None:
        raise ValueError(f"Renamable channel {data.channel_id} not found.")
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
    ch = ctx.guild.get_channel(int(data.channel_id))
    if ch is None or not isinstance(ch, discord.TextChannel):
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
