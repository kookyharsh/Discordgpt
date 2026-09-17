from typing import Literal

import discord
import needle
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel
from src.permissions.permission_engine import HierarchyEngine

# --- Synthetic Tools for Needle Engine Control ---


@needle.tool
def ask_clarification(question: str) -> str:
    """Ask the user a clarifying question when details or target parameters are ambiguous or missing.

    Args:
        question: Concise explanation of what detail or choice is missing.
    """
    return f"Clarification requested: {question}"


@needle.tool
def chat_reply(message: str) -> str:
    """Send a friendly conversational response or explanation to the user when no Discord operation is required.

    Args:
        message: Conversational message to display to the user.
    """
    return message


# --- 1. Channel Operations ---


class CreateChannelInput(BaseModel):
    name: str = Field(..., max_length=100)
    type: Literal["text", "voice", "category", "forum"] = "text"
    category_id: str | None = None
    topic: str | None = Field(None, max_length=1024)


async def create_channel_handler(ctx, input_data: CreateChannelInput):
    channel_type = discord.ChannelType.text
    if input_data.type == "voice":
        channel_type = discord.ChannelType.voice
    elif input_data.type == "category":
        channel_type = discord.ChannelType.category
    elif input_data.type == "forum":
        channel_type = discord.ChannelType.forum

    category = None
    if input_data.category_id:
        category = ctx.guild.get_channel(int(input_data.category_id))

    ch = await ctx.guild.create_channel(
        name=input_data.name,
        channel_type=channel_type,
        category=category,
        topic=input_data.topic,
    )
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
    ch = ctx.guild.get_channel(int(input_data.channel_id))
    if not ch:
        ch = await ctx.guild.fetch_channel(int(input_data.channel_id))
    name = ch.name
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


async def edit_channel_handler(ctx, input_data: EditChannelInput):
    ch = ctx.guild.get_channel(int(input_data.channel_id))
    kwargs = {}
    if input_data.name:
        kwargs["name"] = input_data.name
    if input_data.topic is not None:
        kwargs["topic"] = input_data.topic
    if input_data.nsfw is not None and hasattr(ch, "edit"):
        kwargs["nsfw"] = input_data.nsfw

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

# --- 2. Role Operations ---


class CreateRoleInput(BaseModel):
    name: str = Field(..., max_length=100)
    color: str | None = None
    hoist: bool | None = None
    mentionable: bool | None = None


async def create_role_handler(ctx, input_data: CreateRoleInput):
    color = discord.Color.default()
    if input_data.color:
        try:
            color = discord.Color(int(input_data.color.replace("#", ""), 16))
        except ValueError:
            pass

    role = await ctx.guild.create_role(
        name=input_data.name,
        color=color,
        hoist=input_data.hoist or False,
        mentionable=input_data.mentionable or False,
    )
    return {"role_id": str(role.id), "name": role.name}


ActionRegistry.register(
    ActionDefinition(
        type="create_role",
        description="Creates a new role in the server.",
        input_schema=CreateRoleInput,
        required_bot_permissions=discord.Permissions(manage_roles=True),
        required_user_permissions=discord.Permissions(manage_roles=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_role_handler,
    )
)


class AssignRoleInput(BaseModel):
    member_id: str
    role_id: str


async def assign_role_handler(ctx, input_data: AssignRoleInput):
    role = ctx.guild.get_role(int(input_data.role_id))
    if not role:
        raise ValueError(f"Role {input_data.role_id} not found.")

    ok, reason = HierarchyEngine.can_bot_manage_role(ctx.guild, role)
    if not ok:
        raise ValueError(reason)

    member = ctx.guild.get_member(int(input_data.member_id))
    if not member:
        member = await ctx.guild.fetch_member(int(input_data.member_id))

    await member.add_roles(role)
    return {"member_id": str(member.id), "role_id": str(role.id), "assigned": True}


ActionRegistry.register(
    ActionDefinition(
        type="assign_role",
        description="Assigns a role to a member.",
        input_schema=AssignRoleInput,
        required_bot_permissions=discord.Permissions(manage_roles=True),
        required_user_permissions=discord.Permissions(manage_roles=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=assign_role_handler,
    )
)

# --- 3. Member Operations ---


class TimeoutMemberInput(BaseModel):
    member_id: str
    duration_seconds: int = Field(..., ge=1, le=2419200)
    reason: str | None = None


async def timeout_member_handler(ctx, input_data: TimeoutMemberInput):
    member = ctx.guild.get_member(int(input_data.member_id))
    if not member:
        member = await ctx.guild.fetch_member(int(input_data.member_id))

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


class BanMemberInput(BaseModel):
    member_id: str
    reason: str | None = None
    delete_message_seconds: int | None = Field(None, ge=0, le=604800)


async def ban_member_handler(ctx, input_data: BanMemberInput):
    member = ctx.guild.get_member(int(input_data.member_id))
    if member:
        ok, reason = HierarchyEngine.can_bot_manage_member(ctx.guild, member)
        if not ok:
            raise ValueError(reason)

    await ctx.guild.ban(
        user=discord.Object(id=int(input_data.member_id)),
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

# --- 4. Message Operations ---


class SendMessageInput(BaseModel):
    channel_id: str
    content: str = Field(..., min_length=1, max_length=2000)


async def send_message_handler(ctx, input_data: SendMessageInput):
    ch = ctx.guild.get_channel(int(input_data.channel_id))
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


# Export Tool Definitions to tools/discord_tools.json
def export_tools_json(filepath: str = "tools/discord_tools.json"):
    import json

    schemas = []
    for act in ActionRegistry.get_all():
        schemas.append(
            {
                "name": act.type,
                "description": act.description,
                "parameters": act.input_schema.model_json_schema(),
                "risk_level": act.risk_level.value,
                "confirmation_policy": act.confirmation_policy.value,
            }
        )
    with open(filepath, "w") as f:
        json.dump(schemas, f, indent=2)
