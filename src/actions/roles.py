"""Role actions: create/assign/remove/edit/delete.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import coerce_snowflake
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel
from src.permissions.permission_engine import HierarchyEngine


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
    from src.actions._helpers import resolve_member

    role = ctx.guild.get_role(coerce_snowflake(input_data.role_id, "role"))
    if not role:
        raise ValueError(f"Role {input_data.role_id} not found.")

    ok, reason = HierarchyEngine.can_bot_manage_role(ctx.guild, role)
    if not ok:
        raise ValueError(reason)

    member = await resolve_member(ctx.guild, input_data.member_id)
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


class DeleteRoleInput(BaseModel):
    role_id: str
    reason: str | None = Field(None, max_length=512)


async def delete_role_handler(ctx, data: DeleteRoleInput):
    role = ctx.guild.get_role(coerce_snowflake(data.role_id, "role"))
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
    from src.actions._helpers import resolve_member

    role = ctx.guild.get_role(coerce_snowflake(data.role_id, "role"))
    if role is None:
        raise ValueError(f"Role {data.role_id} not found.")
    member = await resolve_member(ctx.guild, data.member_id)
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
    role = ctx.guild.get_role(coerce_snowflake(data.role_id, "role"))
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
