from types import SimpleNamespace

import discord

from src.permissions.permission_engine import HierarchyEngine, PermissionEngine


def _member(**perms):
    return SimpleNamespace(guild_permissions=discord.Permissions(**perms))


def _guild(me):
    return SimpleNamespace(me=me)


def test_bot_permissions_allow():
    guild = _guild(_member(manage_channels=True))
    ok, missing = PermissionEngine.check_bot_permissions(
        guild, discord.Permissions(manage_channels=True)
    )
    assert ok and missing == []


def test_bot_permissions_deny_missing():
    guild = _guild(_member())
    ok, missing = PermissionEngine.check_bot_permissions(
        guild, discord.Permissions(manage_channels=True)
    )
    assert not ok and missing == ["MANAGE_CHANNELS"]


def test_bot_permissions_no_me():
    ok, missing = PermissionEngine.check_bot_permissions(
        _guild(None), discord.Permissions(manage_channels=True)
    )
    assert not ok and missing


def test_user_permissions_allow_and_deny():
    assert (
        PermissionEngine.check_user_permissions(
            _member(send_messages=True), discord.Permissions(send_messages=True)
        )[0]
        is True
    )
    ok, missing = PermissionEngine.check_user_permissions(
        _member(), discord.Permissions(ban_members=True)
    )
    assert not ok and missing == ["BAN_MEMBERS"]


def test_user_without_guild_permissions_object_denied():
    ok, missing = PermissionEngine.check_user_permissions(
        SimpleNamespace(), discord.Permissions(send_messages=True)
    )
    assert not ok and missing


def test_hierarchy_owner_and_position():
    guild = SimpleNamespace(owner_id=1)
    owner = SimpleNamespace(id=1, guild=guild, top_role=SimpleNamespace(position=0))
    admin = SimpleNamespace(id=2, guild=guild, top_role=SimpleNamespace(position=10))
    peon = SimpleNamespace(id=3, guild=guild, top_role=SimpleNamespace(position=2))
    assert HierarchyEngine.can_actor_manage_member(owner, admin) is True
    assert HierarchyEngine.can_actor_manage_member(admin, peon) is True
    assert HierarchyEngine.can_actor_manage_member(peon, admin) is False
    assert HierarchyEngine.can_actor_manage_member(admin, owner) is False
