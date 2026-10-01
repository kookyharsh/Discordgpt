"""AutoMod actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

from typing import Literal

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


class CreateAutomodVariantInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    variant: Literal["mention_spam", "keyword_preset", "member_profile"]
    limit: int = Field(5, ge=1, le=50)
    presets: list[str] = Field(default_factory=list, max_length=3)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    actions: list[str] = Field(default_factory=lambda: ["block_message"], max_length=3)
    reason: str | None = Field(None, max_length=512)


async def create_automod_variant_handler(ctx, data: CreateAutomodVariantInput):
    if data.variant == "mention_spam":
        trigger = discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.mention_spam, mention_spam_limit=data.limit)
    elif data.variant == "keyword_preset":
        try: preset_values = [getattr(discord.AutoModPresets, p) for p in data.presets]
        except AttributeError: raise ValueError("Unknown AutoMod keyword preset.") from None
        trigger = discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.keyword_preset, presets=preset_values)
    else:
        trigger = discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.member_profile, allow_list=data.keywords)
    action_values = []
    for name in data.actions:
        try: action_values.append(discord.AutoModRuleAction(type=getattr(discord.AutoModRuleActionType, name)))
        except AttributeError: raise ValueError(f"Unknown AutoMod action '{name}'.") from None
    rule = await ctx.guild.create_automod_rule(name=data.name, event_type=discord.AutoModRuleEventType.message_send, trigger=trigger, actions=action_values, reason=data.reason)
    return {"rule_id": str(rule.id), "name": rule.name, "variant": data.variant}


ActionRegistry.register(ActionDefinition(type="create_automod_rule", description="Creates a mention-spam, keyword-preset, or member-profile AutoMod rule.", input_schema=CreateAutomodVariantInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=create_automod_variant_handler))


class EditAutomodRuleInput(BaseModel):
    rule_id: str
    enabled: bool | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=512)


async def edit_automod_rule_handler(ctx, data: EditAutomodRuleInput):
    rule = await ctx.guild.fetch_automod_rule(int(data.rule_id))
    kwargs = {k: v for k, v in {"enabled": data.enabled, "name": data.name, "reason": data.reason}.items() if v is not None}
    if not kwargs: raise ValueError("Provide enabled and/or name.")
    await rule.edit(**kwargs)
    return {"rule_id": data.rule_id, "updated": True}


ActionRegistry.register(ActionDefinition(type="edit_automod_rule", description="Enables, disables, or renames an existing AutoMod rule.", input_schema=EditAutomodRuleInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=edit_automod_rule_handler))


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
