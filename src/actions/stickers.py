"""Guild sticker management."""
from __future__ import annotations

import base64
from io import BytesIO

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class ListStickersInput(BaseModel): pass
async def list_stickers_handler(ctx, data):
    stickers = await ctx.guild.fetch_stickers()
    return {"stickers": [{"sticker_id": str(s.id), "name": s.name, "description": s.description, "emoji": s.emoji} for s in stickers]}
ActionRegistry.register(ActionDefinition(type="list_stickers", description="Lists guild stickers available for sending or management.", input_schema=ListStickersInput, required_bot_permissions=discord.Permissions(read_message_history=True), required_user_permissions=discord.Permissions.none(), risk_level=RiskLevel.LOW, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=list_stickers_handler))

class CreateStickerInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=30)
    description: str = Field(..., min_length=1, max_length=100)
    emoji: str = Field(..., min_length=1, max_length=2)
    image_base64: str = Field(..., description="PNG/APNG/Lottie bytes, base64 encoded, max 512KB")
    reason: str | None = Field(None, max_length=512)
async def create_sticker_handler(ctx, data: CreateStickerInput):
    try: raw = base64.b64decode(data.image_base64, validate=True)
    except Exception: raise ValueError("image_base64 is not valid base64.") from None
    if len(raw) > 512 * 1024: raise ValueError("Sticker image must be under 512KB.")
    sticker = await ctx.guild.create_sticker(name=data.name, description=data.description, emoji=data.emoji, file=discord.File(BytesIO(raw), filename="sticker.png"), reason=data.reason)
    return {"sticker_id": str(sticker.id), "name": sticker.name}
ActionRegistry.register(ActionDefinition(type="create_sticker", description="Creates a guild sticker from bounded base64 image data.", input_schema=CreateStickerInput, required_bot_permissions=discord.Permissions(manage_emojis_and_stickers=True), required_user_permissions=discord.Permissions(manage_emojis_and_stickers=True), risk_level=RiskLevel.MEDIUM, confirmation_policy=ConfirmationPolicy.NOT_REQUIRED, handler=create_sticker_handler))

class DeleteStickerInput(BaseModel):
    sticker_id: str
    reason: str | None = Field(None, max_length=512)
async def delete_sticker_handler(ctx, data: DeleteStickerInput):
    await ctx.guild.delete_sticker(discord.Object(id=int(data.sticker_id)), reason=data.reason)
    return {"sticker_id": data.sticker_id, "deleted": True}
ActionRegistry.register(ActionDefinition(type="delete_sticker", description="Deletes a guild sticker by ID.", input_schema=DeleteStickerInput, required_bot_permissions=discord.Permissions(manage_emojis_and_stickers=True), required_user_permissions=discord.Permissions(manage_emojis_and_stickers=True), risk_level=RiskLevel.HIGH, confirmation_policy=ConfirmationPolicy.REQUIRED, handler=delete_sticker_handler))
