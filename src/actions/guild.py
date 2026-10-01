"""Guild actions: info/edit/bans.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class GetGuildInfoInput(BaseModel):
    pass


async def get_guild_info_handler(ctx, data: GetGuildInfoInput):
    guild = ctx.guild
    return {
        "guild_id": str(guild.id),
        "name": guild.name,
        "member_count": guild.member_count,
        "channel_count": len(guild.channels),
        "role_count": len(guild.roles),
        "owner_id": str(guild.owner_id) if guild.owner_id else None,
        "description": guild.description,
    }


ActionRegistry.register(
    ActionDefinition(
        type="get_guild_info",
        description="Returns basic guild info: name, member/channel/role counts.",
        input_schema=GetGuildInfoInput,
        required_bot_permissions=discord.Permissions.none(),
        required_user_permissions=discord.Permissions.none(),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=get_guild_info_handler,
    )
)


class GetWelcomeScreenInput(BaseModel): pass
async def get_welcome_screen_handler(ctx, data):
    screen = await ctx.guild.welcome_screen()
    return {"enabled": screen.enabled, "description": screen.description, "channels": [{"channel_id": str(c.channel.id), "description": c.description, "emoji": c.emoji_name} for c in screen.welcome_channels]}
ActionRegistry.register(ActionDefinition(type="get_welcome_screen", description="Reads the guild welcome screen and configured welcome channels.", input_schema=GetWelcomeScreenInput, required_bot_permissions=discord.Permissions(view_guild_insights=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=get_welcome_screen_handler))

class EditWelcomeScreenInput(BaseModel):
    description: str | None = Field(None, max_length=140)
    enabled: bool | None = None
    reason: str | None = Field(None, max_length=512)
async def edit_welcome_screen_handler(ctx, data):
    kwargs = {k: v for k, v in {"description": data.description, "enabled": data.enabled, "reason": data.reason}.items() if v is not None}
    if not kwargs: raise ValueError("Provide description and/or enabled.")
    screen = await ctx.guild.edit_welcome_screen(**kwargs)
    return {"enabled": screen.enabled, "description": screen.description, "updated": True}
ActionRegistry.register(ActionDefinition(type="edit_welcome_screen", description="Edits the guild welcome screen description or enabled state.", input_schema=EditWelcomeScreenInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=edit_welcome_screen_handler))

class GetOnboardingInput(BaseModel): pass
async def get_onboarding_handler(ctx, data):
    onboarding = await ctx.guild.onboarding()
    return {"enabled": onboarding.enabled, "mode": str(onboarding.mode), "prompts": [{"id": str(p.id), "title": p.title, "required": p.required} for p in onboarding.prompts]}
ActionRegistry.register(ActionDefinition(type="get_onboarding", description="Reads guild onboarding settings and prompts.", input_schema=GetOnboardingInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=get_onboarding_handler))

class EditOnboardingInput(BaseModel):
    enabled: bool | None = None
    reason: str | None = Field(None, max_length=512)
async def edit_onboarding_handler(ctx, data):
    onboarding = await ctx.guild.onboarding()
    if data.enabled is None: raise ValueError("Provide enabled=true or false.")
    await ctx.guild.edit_onboarding(prompts=onboarding.prompts, default_channels=onboarding.default_channel_ids, enabled=data.enabled, mode=onboarding.mode, reason=data.reason)
    return {"enabled": data.enabled, "updated": True}
ActionRegistry.register(ActionDefinition(type="edit_onboarding", description="Enables or disables guild onboarding while preserving its existing prompts and default channels.", input_schema=EditOnboardingInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=edit_onboarding_handler))

class GetWidgetInput(BaseModel): pass
async def get_widget_handler(ctx, data):
    widget = await ctx.guild.widget()
    return {"enabled": widget.enabled, "channel_id": str(widget.channel_id) if widget.channel_id else None}
ActionRegistry.register(ActionDefinition(type="get_widget", description="Reads the guild widget enabled state and channel.", input_schema=GetWidgetInput, required_bot_permissions=discord.Permissions(view_guild_insights=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=get_widget_handler))

class EditWidgetInput(BaseModel):
    enabled: bool | None = None
    channel_id: str | None = None
    reason: str | None = Field(None, max_length=512)
async def edit_widget_handler(ctx, data):
    kwargs = {"enabled": data.enabled, "reason": data.reason}
    if data.channel_id: kwargs["channel"] = await ctx.guild.fetch_channel(int(data.channel_id))
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    if not kwargs: raise ValueError("Provide enabled and/or channel_id.")
    await ctx.guild.edit_widget(**kwargs)
    return {"updated": True}
ActionRegistry.register(ActionDefinition(type="edit_widget", description="Edits guild widget visibility and optional widget channel.", input_schema=EditWidgetInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=edit_widget_handler))

class GetVanityInput(BaseModel): pass
async def get_vanity_handler(ctx, data):
    invite = await ctx.guild.vanity_invite()
    return {"code": invite.code if invite else None, "url": invite.url if invite else None, "uses": invite.uses if invite else None}
ActionRegistry.register(ActionDefinition(type="get_vanity_url", description="Reads the guild vanity invite when the guild is eligible for one.", input_schema=GetVanityInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=get_vanity_handler))

class ListIntegrationsInput(BaseModel): pass
async def list_integrations_handler(ctx, data):
    integrations = await ctx.guild.integrations()
    return {"integrations": [{"id": str(i.id), "name": i.name, "type": i.type, "enabled": i.enabled} for i in integrations]}
ActionRegistry.register(ActionDefinition(type="list_integrations", description="Lists guild integrations such as Twitch or YouTube connections.", input_schema=ListIntegrationsInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=list_integrations_handler))

class ListTemplatesInput(BaseModel): pass
async def list_templates_handler(ctx, data):
    templates = await ctx.guild.templates()
    return {"templates": [{"code": t.code, "name": t.name, "description": t.description, "creator_id": str(t.creator.id) if t.creator else None} for t in templates]}
ActionRegistry.register(ActionDefinition(type="list_templates", description="Lists server templates associated with the guild.", input_schema=ListTemplatesInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=list_templates_handler))

class CreateTemplateInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=120)
async def create_template_handler(ctx, data):
    template = await ctx.guild.create_template(name=data.name, description=data.description)
    return {"code": template.code, "name": template.name, "created": True}
ActionRegistry.register(ActionDefinition(type="create_template", description="Creates a reusable server template from the current guild.", input_schema=CreateTemplateInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=create_template_handler))

class TemplateCodeInput(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
async def sync_template_handler(ctx, data):
    template = next((t for t in await ctx.guild.templates() if t.code == data.code), None)
    if template is None: raise ValueError(f"Template {data.code} not found.")
    await template.sync()
    return {"code": template.code, "synced": True}
ActionRegistry.register(ActionDefinition(type="sync_template", description="Syncs a Discord server template with the current guild.", input_schema=TemplateCodeInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=sync_template_handler))
async def delete_template_handler(ctx, data):
    template = next((t for t in await ctx.guild.templates() if t.code == data.code), None)
    if template is None: raise ValueError(f"Template {data.code} not found.")
    await template.delete()
    return {"code": data.code, "deleted": True}
ActionRegistry.register(ActionDefinition(type="delete_template", description="Deletes a Discord server template by template code.", input_schema=TemplateCodeInput, required_bot_permissions=discord.Permissions(manage_guild=True), required_user_permissions=discord.Permissions(manage_guild=True), risk_level=RiskLevel.HIGH, confirmation_policy=ConfirmationPolicy.REQUIRED, handler=delete_template_handler))


class EditGuildInput(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    reason: str | None = Field(None, max_length=512)


async def edit_guild_handler(ctx, data: EditGuildInput):
    if data.name is None and data.description is None:
        raise ValueError("Provide name and/or description to update.")
    kwargs: dict = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.description is not None:
        kwargs["description"] = data.description
    if data.reason:
        kwargs["reason"] = data.reason
    guild = await ctx.guild.edit(**kwargs)
    return {"guild_id": str(guild.id), "name": guild.name}


ActionRegistry.register(
    ActionDefinition(
        type="edit_guild",
        description="Edits guild name and/or description.",
        input_schema=EditGuildInput,
        required_bot_permissions=discord.Permissions(manage_guild=True),
        required_user_permissions=discord.Permissions(manage_guild=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=edit_guild_handler,
    )
)


class ListBansInput(BaseModel):
    limit: int = Field(50, ge=1, le=200)


async def list_bans_handler(ctx, data: ListBansInput):
    entries = []
    count = 0
    async for ban in ctx.guild.bans(limit=data.limit):
        entries.append({"user_id": str(ban.user.id), "user": str(ban.user)})
        count += 1
        if count >= data.limit:
            break
    return {"bans": entries}


ActionRegistry.register(
    ActionDefinition(
        type="list_bans",
        description="Lists banned users in the guild.",
        input_schema=ListBansInput,
        required_bot_permissions=discord.Permissions(ban_members=True),
        required_user_permissions=discord.Permissions(ban_members=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_bans_handler,
    )
)
