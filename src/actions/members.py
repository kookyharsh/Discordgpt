"""Member/moderation actions: timeout/kick/ban/nickname/voice state.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import coerce_snowflake, resolve_guild_channel, resolve_member
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel
from src.permissions.permission_engine import HierarchyEngine


class TimeoutMemberInput(BaseModel):
    member_id: str
    duration_seconds: int = Field(..., ge=1, le=2419200)
    reason: str | None = None


async def timeout_member_handler(ctx, input_data: TimeoutMemberInput):
    member = await resolve_member(ctx.guild, input_data.member_id)
    ok, reason = HierarchyEngine.can_bot_manage_member(ctx.guild, member)
    if not ok:
        raise ValueError(reason)

    import datetime

    delta = datetime.timedelta(seconds=input_data.duration_seconds)
    await member.timeout(delta, reason=input_data.reason)
    return {
        "member_id": str(member.id),
        "duration_seconds": input_data.duration_seconds,
        "timed_out": True,
    }


ActionRegistry.register(
    ActionDefinition(
        type="timeout_member",
        description="Times out a member for a specified duration in seconds.",
        input_schema=TimeoutMemberInput,
        required_bot_permissions=discord.Permissions(moderate_members=True),
        required_user_permissions=discord.Permissions(moderate_members=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.REQUIRED,
        handler=timeout_member_handler,
    )
)


class UntimeoutMemberInput(BaseModel):
    member_id: str
    reason: str | None = Field(None, max_length=512)


async def untimeout_member_handler(ctx, data: UntimeoutMemberInput):
    member = await resolve_member(ctx.guild, data.member_id)
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


class KickMemberInput(BaseModel):
    member_id: str
    reason: str | None = Field(None, max_length=512)


async def kick_member_handler(ctx, data: KickMemberInput):
    member = await resolve_member(ctx.guild, data.member_id)
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


class BanMemberInput(BaseModel):
    member_id: str
    reason: str | None = None
    delete_message_seconds: int | None = Field(None, ge=0, le=604800)


async def ban_member_handler(ctx, input_data: BanMemberInput):
    member_id = coerce_snowflake(input_data.member_id, "member")
    member = ctx.guild.get_member(member_id)
    if member:
        ok, reason = HierarchyEngine.can_bot_manage_member(ctx.guild, member)
        if not ok:
            raise ValueError(reason)

    await ctx.guild.ban(
        user=discord.Object(id=member_id),
        reason=input_data.reason,
        delete_message_seconds=input_data.delete_message_seconds or 0,
    )
    return {"member_id": input_data.member_id, "banned": True}


ActionRegistry.register(
    ActionDefinition(
        type="ban_member",
        description="Bans a member from the guild.",
        input_schema=BanMemberInput,
        required_bot_permissions=discord.Permissions(ban_members=True),
        required_user_permissions=discord.Permissions(ban_members=True),
        risk_level=RiskLevel.HIGH,
        confirmation_policy=ConfirmationPolicy.REQUIRED,
        handler=ban_member_handler,
    )
)


class UnbanMemberInput(BaseModel):
    user_id: str
    reason: str | None = Field(None, max_length=512)


async def unban_member_handler(ctx, data: UnbanMemberInput):
    user_id = coerce_snowflake(data.user_id, "member")
    await ctx.guild.unban(user=discord.Object(id=user_id), reason=data.reason)
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


class SetNicknameInput(BaseModel):
    member_id: str
    nickname: str | None = Field(None, max_length=32)
    reason: str | None = Field(None, max_length=512)


async def set_nickname_handler(ctx, data: SetNicknameInput):
    member = await resolve_member(ctx.guild, data.member_id)
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
    member = await resolve_member(ctx.guild, data.member_id)
    if member.voice is None or member.voice.channel is None:
        raise ValueError(f"{member} is not in a voice channel.")
    if data.channel_id:
        target = await resolve_guild_channel(ctx.guild, data.channel_id)
        if not isinstance(target, discord.VoiceChannel):
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


class MuteMemberInput(BaseModel):
    member_id: str
    muted: bool = True
    reason: str | None = Field(None, max_length=512)


async def mute_member_handler(ctx, data: MuteMemberInput):
    member = await resolve_member(ctx.guild, data.member_id)
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
    member = await resolve_member(ctx.guild, data.member_id)
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
