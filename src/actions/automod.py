"""AutoMod actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class ListAutomodRulesInput(BaseModel):
    pass


async def list_automod_rules_handler(ctx, data: ListAutomodRulesInput):
    rules = await ctx.guild.fetch_automod_rules()
    return {
        "rules": [{"rule_id": str(r.id), "name": r.name, "enabled": r.enabled} for r in rules[:25]]
    }


ActionRegistry.register(
    ActionDefinition(
        type="list_automod_rules",
        description="Lists AutoMod rules in the guild.",
        input_schema=ListAutomodRulesInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_automod_rules_handler,
    )
)


class CreateKeywordRuleInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    keywords: list[str] = Field(..., min_length=1, max_length=20)
    reason: str | None = Field(None, max_length=512)


async def create_keyword_rule_handler(ctx, data: CreateKeywordRuleInput):
    trigger = discord.AutoModTrigger(
        type=discord.AutoModRuleTriggerType.keyword,
        keyword_filter=data.keywords,
    )
    action = discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)
    rule = await ctx.guild.create_automod_rule(
        name=data.name,
        event_type=discord.AutoModRuleEventType.message_send,
        trigger=trigger,
        actions=[action],
        reason=data.reason,
    )
    return {"rule_id": str(rule.id), "name": rule.name}


ActionRegistry.register(
    ActionDefinition(
        type="create_keyword_rule",
        description="Creates an AutoMod keyword block rule.",
        input_schema=CreateKeywordRuleInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_keyword_rule_handler,
    )
)


class DeleteAutomodRuleInput(BaseModel):
    rule_id: str


async def delete_automod_rule_handler(ctx, data: DeleteAutomodRuleInput):
    rule = await ctx.guild.fetch_automod_rule(int(data.rule_id))
    await rule.delete()
    return {"rule_id": data.rule_id, "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_automod_rule",
        description="Deletes an AutoMod rule by ID.",
        input_schema=DeleteAutomodRuleInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=delete_automod_rule_handler,
    )
)
