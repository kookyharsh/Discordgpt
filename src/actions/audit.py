"""Read-only Discord audit and guild maintenance actions."""
from __future__ import annotations

from datetime import datetime

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class GetAuditLogInput(BaseModel):
    limit: int = Field(25, ge=1, le=100)
    user_id: str | None = None
    action: str | None = Field(None, max_length=64)

async def get_audit_log_handler(ctx, data: GetAuditLogInput):
    kwargs = {"limit": data.limit}
    if data.user_id:
        kwargs["user"] = discord.Object(id=int(data.user_id))
    if data.action:
        try:
            kwargs["action"] = getattr(discord.AuditLogAction, data.action)
        except AttributeError:
            raise ValueError(f"Unknown audit action '{data.action}'.") from None
    entries = []
    async for entry in ctx.guild.audit_logs(**kwargs):
        entries.append({"id": str(entry.id), "action": str(entry.action), "user_id": str(entry.user.id) if entry.user else None, "target_id": str(getattr(entry.target, "id", "")) or None, "created_at": entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else str(entry.created_at), "reason": entry.reason})
    return {"entries": entries}

ActionRegistry.register(ActionDefinition(type="get_audit_log", description="Reads the Discord audit log with optional limit, actor, and action filters; this is Discord telemetry, not the bot's prompt-audit database.", input_schema=GetAuditLogInput, required_bot_permissions=discord.Permissions(view_audit_log=True), required_user_permissions=discord.Permissions(view_audit_log=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=get_audit_log_handler))

class PruneMembersInput(BaseModel):
    days: int = Field(..., ge=1, le=30)
    execute: bool = False
    reason: str | None = Field(None, max_length=512)

async def prune_members_handler(ctx, data: PruneMembersInput):
    if data.execute:
        count = await ctx.guild.prune_members(days=data.days, compute_prune_count=True, reason=data.reason)
        return {"executed": True, "days": data.days, "pruned": count}
    count = await ctx.guild.estimate_pruned_members(days=data.days)
    return {"executed": False, "days": data.days, "estimated": count}

ActionRegistry.register(ActionDefinition(type="prune_members", description="Previews or executes pruning inactive members; execute=true is destructive and requires confirmation.", input_schema=PruneMembersInput, required_bot_permissions=discord.Permissions(kick_members=True), required_user_permissions=discord.Permissions(kick_members=True), risk_level=RiskLevel.HIGH, confirmation_policy=ConfirmationPolicy.REQUIRED, handler=prune_members_handler))
