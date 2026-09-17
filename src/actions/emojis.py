"""Emoji actions.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

import base64

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel


class ListEmojisInput(BaseModel):
    pass


async def list_emojis_handler(ctx, data: ListEmojisInput):
    emojis = await ctx.guild.fetch_emojis()
    return {"emojis": [{"emoji_id": str(e.id), "name": e.name} for e in emojis[:50]]}


ActionRegistry.register(
    ActionDefinition(
        type="list_emojis",
        description="Lists custom emojis in the guild.",
        input_schema=ListEmojisInput,
        required_bot_permissions=discord.Permissions(manage_emojis_and_stickers=True),
        required_user_permissions=discord.Permissions(manage_emojis_and_stickers=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_emojis_handler,
    )
)


class CreateEmojiInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=32)
    image_base64: str = Field(..., description="PNG/JPEG bytes, base64-encoded, max 256KB")
    reason: str | None = Field(None, max_length=512)


async def create_emoji_handler(ctx, data: CreateEmojiInput):
    try:
        image = base64.b64decode(data.image_base64, validate=True)
    except Exception:
        raise ValueError("image_base64 is not valid base64.") from None
    if len(image) > 256 * 1024:
        raise ValueError("Emoji image must be under 256KB.")
    emoji = await ctx.guild.create_custom_emoji(name=data.name, image=image, reason=data.reason)
    return {"emoji_id": str(emoji.id), "name": emoji.name}


ActionRegistry.register(
    ActionDefinition(
        type="create_emoji",
        description="Creates a custom emoji from base64 image data.",
        input_schema=CreateEmojiInput,
        required_bot_permissions=discord.Permissions(manage_emojis_and_stickers=True),
        required_user_permissions=discord.Permissions(manage_emojis_and_stickers=True),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=create_emoji_handler,
    )
)


class DeleteEmojiInput(BaseModel):
    emoji_id: str


async def delete_emoji_handler(ctx, data: DeleteEmojiInput):
    from src.actions._helpers import coerce_snowflake

    emoji_id = coerce_snowflake(data.emoji_id, "emoji")
    emoji = ctx.guild.get_emoji(emoji_id)
    if emoji is None:
        try:
            emoji = await ctx.guild.fetch_emoji(emoji_id)
        except discord.NotFound:
            raise ValueError(f"Emoji {data.emoji_id} not found.") from None
    await emoji.delete()
    return {"emoji_id": data.emoji_id, "deleted": True}


ActionRegistry.register(
    ActionDefinition(
        type="delete_emoji",
        description="Deletes a custom emoji by ID.",
        input_schema=DeleteEmojiInput,
        required_bot_permissions=discord.Permissions(manage_emojis_and_stickers=True),
        required_user_permissions=discord.Permissions(manage_emojis_and_stickers=True),
        risk_level=RiskLevel.MEDIUM,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=delete_emoji_handler,
    )
)
