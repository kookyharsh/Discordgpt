"""Phase B: member name search, disambiguation data, and plan dead-steps."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.actions.plan_executor import execute_action_plan
from src.entities.entity_resolver import EntityResolver


def _member(id, name, display=None, nick=None):
    return SimpleNamespace(id=id, name=name, display_name=display or name, nick=nick)


def _guild(members):
    g = MagicMock(spec=discord.Guild)
    g.members = members
    g.get_member = MagicMock(return_value=None)
    g.fetch_member = AsyncMock(side_effect=discord.NotFound(MagicMock(), "x"))
    return g


async def test_resolve_member_by_username():
    guild = _guild([_member(1, "Bob"), _member(2, "Alice")])
    res = await EntityResolver.resolve_member(guild, "bob")
    assert res.resolved is not None and res.resolved.id == 1


async def test_resolve_member_by_nickname():
    guild = _guild([_member(1, "Robert", display="Bobby", nick="Bob")])
    res = await EntityResolver.resolve_member(guild, "bobby")
    assert res.resolved is not None and res.resolved.id == 1


async def test_resolve_member_ambiguous():
    guild = _guild([_member(1, "Bob Smith"), _member(2, "Bob Jones")])
    res = await EntityResolver.resolve_member(guild, "bob")
    assert res.resolved is None and res.ambiguous and len(res.matches or []) == 2


async def test_resolve_member_not_found():
    guild = _guild([_member(1, "Bob")])
    res = await EntityResolver.resolve_member(guild, "Zelda")
    assert res.resolved is None and res.not_found


async def test_resolve_member_id_still_works():
    guild = _guild([])
    guild.get_member = MagicMock(return_value=_member(7, "Bob"))
    res = await EntityResolver.resolve_member(guild, "123456789012345678")
    guild.get_member.assert_called_once_with(123456789012345678)
    assert res.resolved is not None


async def test_resolve_channel_bracket_form():
    guild = MagicMock(spec=discord.Guild)
    ch = SimpleNamespace(id=111, name="lobby")
    guild.get_channel = MagicMock(return_value=ch)
    res = await EntityResolver.resolve_channel(guild, "<#111111111111111111>")
    guild.get_channel.assert_called_once_with(111111111111111111)
    assert res.resolved is ch


async def test_resolve_role_bracket_form():
    guild = MagicMock(spec=discord.Guild)
    role = SimpleNamespace(id=333, name="Mods")
    guild.get_role = MagicMock(return_value=role)
    res = await EntityResolver.resolve_role(guild, "<@&333333333333333333>")
    guild.get_role.assert_called_once_with(333333333333333333)
    assert res.resolved is role


async def test_helpers_accept_names_and_brackets():
    from src.actions import _helpers

    guild = _guild([_member(5, "Bob")])
    member = await _helpers.resolve_member(guild, "bob")
    assert member.id == 5
    ch = SimpleNamespace(id=9, name="lobby")
    guild.get_channel = MagicMock(return_value=ch)
    assert await _helpers.resolve_guild_channel(guild, "<#444444444444444444>") is ch
    with pytest.raises(ValueError, match="Multiple members match"):
        await _helpers.resolve_member(_guild([_member(1, "Bob A"), _member(2, "Bob B")]), "bob")
    with pytest.raises(ValueError, match="not found"):
        await _helpers.resolve_member(_guild([_member(1, "Bob")]), "Zelda")


async def test_plan_dead_step_on_unknown_channel():
    guild = MagicMock(spec=discord.Guild)
    guild.channels = []
    guild.get_channel = MagicMock(return_value=None)
    guild.fetch_channel = AsyncMock(side_effect=discord.NotFound(MagicMock(), "x"))
    ctx = SimpleNamespace(guild=guild, guild_id="1", user_id="2", execution_id="e")
    out = await execute_action_plan(
        MagicMock(),
        [{"id": "1", "action": "delete_channel", "parameters": {"channel_name": "nope"}}],
        0,
        ctx,
    )
    assert out["completed"] is True
    assert out["results"][0]["ok"] is False
    assert "not found" in out["results"][0]["error"]
