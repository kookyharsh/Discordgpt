"""Forum post and thread membership actions."""
from __future__ import annotations

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel, resolve_thread
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class CreateForumPostInput(BaseModel):
    channel_id: str
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    applied_tag_ids: list[str] = Field(default_factory=list, max_length=5)
async def create_forum_post_handler(ctx, data):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.ForumChannel): raise ValueError("Target channel is not a forum channel.")
    tags = [t for t in ch.available_tags if str(t.id) in data.applied_tag_ids]
    missing = set(data.applied_tag_ids) - {str(t.id) for t in tags}
    if missing: raise ValueError(f"Forum tag(s) not found: {', '.join(sorted(missing))}.")
    thread = await ch.create_thread(name=data.name, content=data.content, applied_tags=tags)
    return {"thread_id": str(thread.thread.id), "name": thread.thread.name}
ActionRegistry.register(ActionDefinition(type="create_forum_post", description="Creates a forum post with initial content and optional applied forum tags.", input_schema=CreateForumPostInput, required_bot_permissions=discord.Permissions(send_messages=True, create_public_threads=True), required_user_permissions=discord.Permissions(send_messages=True, create_public_threads=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=create_forum_post_handler))

class ListForumTagsInput(BaseModel): channel_id: str
async def list_forum_tags_handler(ctx, data):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.ForumChannel): raise ValueError("Target channel is not a forum channel.")
    return {"tags": [{"tag_id": str(t.id), "name": t.name, "moderated": t.moderated} for t in ch.available_tags]}
ActionRegistry.register(ActionDefinition(type="list_forum_tags", description="Lists available tags for a forum channel.", input_schema=ListForumTagsInput, required_bot_permissions=discord.Permissions(view_channel=True), required_user_permissions=discord.Permissions.none(), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=list_forum_tags_handler))

class SetForumTagsInput(BaseModel):
    thread_id: str
    tag_ids: list[str] = Field(default_factory=list, max_length=5)
async def set_forum_tags_handler(ctx, data):
    thread = await resolve_thread(ctx.guild, data.thread_id)
    parent = thread.parent
    if not isinstance(parent, discord.ForumChannel): raise ValueError("Thread is not a forum post.")
    tags = [t for t in parent.available_tags if str(t.id) in data.tag_ids]
    if len(tags) != len(set(data.tag_ids)): raise ValueError("One or more forum tags were not found.")
    await thread.edit(applied_tags=tags)
    return {"thread_id": data.thread_id, "tag_ids": data.tag_ids, "updated": True}
ActionRegistry.register(ActionDefinition(type="set_forum_tags", description="Replaces the applied tags on a forum post.", input_schema=SetForumTagsInput, required_bot_permissions=discord.Permissions(manage_threads=True), required_user_permissions=discord.Permissions(manage_threads=True), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=set_forum_tags_handler))

class ThreadMemberInput(BaseModel): thread_id: str; user_id: str
async def add_thread_member_handler(ctx, data):
    thread = await resolve_thread(ctx.guild, data.thread_id); await thread.add_user(discord.Object(id=int(data.user_id))); return {"thread_id": data.thread_id, "user_id": data.user_id, "added": True}
async def remove_thread_member_handler(ctx, data):
    thread = await resolve_thread(ctx.guild, data.thread_id); await thread.remove_user(discord.Object(id=int(data.user_id))); return {"thread_id": data.thread_id, "user_id": data.user_id, "removed": True}
for _name, _handler, _verb in [("add_thread_member", add_thread_member_handler, "Adds"), ("remove_thread_member", remove_thread_member_handler, "Removes")]:
    ActionRegistry.register(ActionDefinition(type=_name, description=f"{_verb} a user to or from a Discord thread by ID.", input_schema=ThreadMemberInput, required_bot_permissions=discord.Permissions(manage_threads=True), required_user_permissions=discord.Permissions(manage_threads=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=_handler))
