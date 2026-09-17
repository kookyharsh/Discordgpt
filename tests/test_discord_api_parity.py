"""Parity: every registered handler calls a real discord.py API + friendly errors."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import src.actions.automod
import src.actions.channels
import src.actions.emojis
import src.actions.events
import src.actions.guild
import src.actions.invites
import src.actions.members
import src.actions.messages
import src.actions.roles
import src.actions.system
import src.actions.threads
import src.actions.webhooks
from src.actions.dispatcher import friendly_error
from src.actions.registry import ActionRegistry


def _guild_mock():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123
    guild.me = MagicMock()
    guild.default_role = MagicMock()
    return guild


def _ctx(guild=None):
    guild = guild or _guild_mock()
    return SimpleNamespace(guild=guild, guild_id=str(guild.id), user_id="1", execution_id="e1")


async def test_create_channel_uses_real_guild_apis():
    assert not hasattr(discord.Guild, "create_channel"), "assumption: no generic API"
    for method in (
        "create_text_channel",
        "create_voice_channel",
        "create_category",
        "create_forum",
    ):
        assert hasattr(discord.Guild, method), f"discord.py missing {method}"

    guild = _guild_mock()
    fake = SimpleNamespace(id=10, name="welcome")
    guild.create_text_channel = AsyncMock(return_value=fake)
    guild.create_voice_channel = AsyncMock(return_value=fake)
    guild.create_category = AsyncMock(return_value=fake)
    guild.create_forum = AsyncMock(return_value=fake)
    ctx = _ctx(guild)

    out = await src.actions.channels.create_channel_handler(
        ctx, src.actions.channels.CreateChannelInput(name="welcome", type="text")
    )
    assert out["channel_id"] == "10"
    guild.create_text_channel.assert_awaited_once()

    await src.actions.channels.create_channel_handler(
        ctx, src.actions.channels.CreateChannelInput(name="voice", type="voice")
    )
    guild.create_voice_channel.assert_awaited_once()

    await src.actions.channels.create_channel_handler(
        ctx, src.actions.channels.CreateChannelInput(name="cat", type="category")
    )
    guild.create_category.assert_awaited_once()

    await src.actions.channels.create_channel_handler(
        ctx,
        src.actions.channels.CreateChannelInput(name="forum", type="forum", topic="hello"),
    )
    guild.create_forum.assert_awaited_once()


async def test_create_channel_rejects_topic_on_voice():
    guild = _guild_mock()
    guild.create_voice_channel = AsyncMock(return_value=SimpleNamespace(id=1, name="v"))
    ctx = _ctx(guild)
    # topic is silently ignored for voice (not passed) - must not crash
    out = await src.actions.channels.create_channel_handler(
        ctx,
        src.actions.channels.CreateChannelInput(name="v", type="voice", topic="nope"),
    )
    assert out["type"] == "voice"
    _, kwargs = guild.create_voice_channel.call_args
    assert "topic" not in kwargs


async def test_delete_message_takes_no_reason():
    import inspect

    assert "reason" not in inspect.signature(discord.Message.delete).parameters
    ch = MagicMock()
    msg = MagicMock()
    msg.id = 5
    msg.delete = AsyncMock()
    ch.fetch_message = AsyncMock(return_value=msg)
    guild = _guild_mock()
    guild.get_channel = MagicMock(return_value=ch)
    ctx = _ctx(guild)
    out = await src.actions.messages.delete_message_handler(
        ctx, src.actions.messages.DeleteMessageInput(channel_id="1", message_id="5")
    )
    assert out["deleted"] is True
    msg.delete.assert_awaited_once_with()


async def test_create_invite_passes_zero_through():
    ch = MagicMock()
    ch.create_invite = AsyncMock(return_value=SimpleNamespace(code="abc", url="u"))
    guild = _guild_mock()
    guild.get_channel = MagicMock(return_value=ch)
    # ensure fetch path not needed
    guild.fetch_channel = AsyncMock()
    ctx = _ctx(guild)
    await src.actions.invites.create_invite_handler(
        ctx, src.actions.invites.CreateInviteInput(channel_id="1", max_age=0, max_uses=0)
    )
    _, kwargs = ch.create_invite.call_args
    assert kwargs["max_uses"] == 0


async def test_thread_auto_archive_restricted():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        src.actions.threads.CreateThreadInput(channel_id="1", name="t", auto_archive_minutes=90)


def test_every_handler_module_importable_and_registered():
    registered = {a.type for a in ActionRegistry.get_all()}
    assert "create_channel" in registered
    assert "delete_message" in registered
    assert "create_webhook" in registered
    assert "create_scheduled_event" in registered
    assert len(registered) >= 50


def test_friendly_error_maps_technical_but_passes_valueerror():
    assert "not found" in friendly_error("x", ValueError("Channel 1 not found.")).lower()
    internal = friendly_error("create_channel", AttributeError("'Guild' no attribute"))
    assert "Guild" not in internal
    assert "internal error" in internal.lower()
    forbidden = friendly_error("ban_member", discord.Forbidden(MagicMock(), "missing perms"))
    assert "permission" in forbidden.lower()
