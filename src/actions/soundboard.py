"""Soundboard sound management and voice-channel effects; no audio playback."""
from __future__ import annotations

import base64

import discord
from pydantic import BaseModel, Field

from src.actions._helpers import resolve_guild_channel
from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class ListSoundboardSoundsInput(BaseModel): pass
async def list_soundboard_sounds_handler(ctx, data):
    sounds = await ctx.guild.fetch_soundboard_sounds()
    return {"sounds": [{"sound_id": str(s.id), "name": s.name, "volume": s.volume, "emoji": s.emoji_name} for s in sounds]}
ActionRegistry.register(ActionDefinition(type="list_soundboard_sounds", description="Lists custom and default soundboard sounds visible to the guild.", input_schema=ListSoundboardSoundsInput, required_bot_permissions=discord.Permissions(view_channel=True), required_user_permissions=discord.Permissions.none(), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=list_soundboard_sounds_handler))

class CreateSoundboardSoundInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    sound_base64: str = Field(..., description="MP3/OGG sound bytes, base64 encoded, max 512KB")
    volume: float = Field(1.0, ge=0.0, le=1.0)
    emoji: str | None = Field(None, max_length=2)
    reason: str | None = Field(None, max_length=512)
async def create_soundboard_sound_handler(ctx, data):
    try: raw = base64.b64decode(data.sound_base64, validate=True)
    except Exception: raise ValueError("sound_base64 is not valid base64.") from None
    if len(raw) > 512 * 1024: raise ValueError("Sound must be under 512KB.")
    sound = await ctx.guild.create_soundboard_sound(name=data.name, sound=raw, volume=data.volume, emoji=data.emoji, reason=data.reason)
    return {"sound_id": str(sound.id), "name": sound.name}
ActionRegistry.register(ActionDefinition(type="create_soundboard_sound", description="Creates a bounded custom soundboard sound; does not connect to voice or play audio streams.", input_schema=CreateSoundboardSoundInput, required_bot_permissions=discord.Permissions(create_expressions=True), required_user_permissions=discord.Permissions(create_expressions=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=create_soundboard_sound_handler))

class DeleteSoundboardSoundInput(BaseModel):
    sound_id: str
    reason: str | None = Field(None, max_length=512)
async def delete_soundboard_sound_handler(ctx, data):
    sound = ctx.guild.get_soundboard_sound(int(data.sound_id)) or await ctx.guild.fetch_soundboard_sound(int(data.sound_id))
    await sound.delete(reason=data.reason)
    return {"sound_id": data.sound_id, "deleted": True}
ActionRegistry.register(ActionDefinition(type="delete_soundboard_sound", description="Deletes a custom soundboard sound by ID.", input_schema=DeleteSoundboardSoundInput, required_bot_permissions=discord.Permissions(create_expressions=True), required_user_permissions=discord.Permissions(create_expressions=True), risk_level=RiskLevel.HIGH, confirmation_policy=ConfirmationPolicy.REQUIRED, handler=delete_soundboard_sound_handler))

class SendSoundboardSoundInput(BaseModel):
    channel_id: str
    sound_id: str
async def send_soundboard_sound_handler(ctx, data):
    ch = await resolve_guild_channel(ctx.guild, data.channel_id)
    if not isinstance(ch, discord.VoiceChannel): raise ValueError("Soundboard effects require a voice channel.")
    sound = ctx.guild.get_soundboard_sound(int(data.sound_id)) or await ctx.guild.fetch_soundboard_sound(int(data.sound_id))
    await ch.send_sound(sound)
    return {"channel_id": data.channel_id, "sound_id": data.sound_id, "sent": True}
ActionRegistry.register(ActionDefinition(type="send_soundboard_sound", description="Triggers a soundboard effect in a voice channel without implementing voice playback.", input_schema=SendSoundboardSoundInput, required_bot_permissions=discord.Permissions(use_soundboard=True), required_user_permissions=discord.Permissions(use_soundboard=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=send_soundboard_sound_handler))
