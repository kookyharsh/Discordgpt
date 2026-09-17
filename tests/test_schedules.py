"""Scheduling: delay/cron parsing + schedule/list/cancel validation (DB-free)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import discord
import pytest

import src.actions.channels
import src.actions.messages  # noqa: F401
import src.actions.schedules as sched_mod
from src.actions.schedules import (
    cancel_schedule_handler,
    list_schedules_handler,
    schedule_action_handler,
)
from src.ai.fallback_parser import FallbackParser


def _ctx():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123
    me = MagicMock()
    me.guild_permissions = discord.Permissions.all()
    guild.me = me
    member = MagicMock()
    member.guild_permissions = discord.Permissions.all()
    return SimpleNamespace(
        guild=guild, guild_id="123", user_id="9", actor_member=member, settings=None
    )


# ---------- parsing ----------


def test_extract_delay_variants():
    spec, cleaned = FallbackParser.extract_schedule("create channel lobby in 10 seconds")
    assert spec["delay_seconds"] == 10
    assert "lobby" in cleaned
    spec, _ = FallbackParser.extract_schedule("do it after 5 minutes")
    assert spec["delay_seconds"] == 300
    spec, _ = FallbackParser.extract_schedule("do it in 2 hours")
    assert spec["delay_seconds"] == 7200
    spec, _ = FallbackParser.extract_schedule("do it in 1 day")
    assert spec["delay_seconds"] == 86400


def test_extract_cron_variants():
    spec, cleaned = FallbackParser.extract_schedule("send hi every day at 9am")
    assert spec["cron"] == "0 9 * * *"
    assert "send hi" in cleaned
    spec, _ = FallbackParser.extract_schedule("x every monday at 9:30pm")
    assert spec["cron"] == "30 21 * * 1"
    spec, _ = FallbackParser.extract_schedule("x every 15 minutes")
    assert spec["cron"] == "*/15 * * * *"
    spec, _ = FallbackParser.extract_schedule("x every hour")
    assert spec["cron"] == "0 * * * *"


def test_extract_no_schedule():
    spec, _raw = FallbackParser.extract_schedule("purge 20 messages in general")
    assert spec is None
    spec, _ = FallbackParser.extract_schedule("timeout <@123456789012345678> for 10 m")
    assert spec is None


def test_parse_schedule_request_known_inner():
    r = FallbackParser.parse("create channel lobby in 10 seconds")
    assert r["status"] == "schedule_request"
    assert r["action"] == "create_channel"
    assert r["delay_seconds"] == 10


def test_parse_schedule_unknown_inner_defers_to_needle():
    assert FallbackParser.parse("make a channel after 10 seconds") is None


def test_parse_unscheduled_unchanged():
    r = FallbackParser.parse("create channel welcome")
    assert r["action"] == "create_channel" and "status" not in r


# ---------- schedule_action validation (no DB) ----------


async def test_rejects_unknown_action():
    ctx = _ctx()
    with pytest.raises(ValueError, match="Unknown action"):
        await schedule_action_handler(
            ctx, sched_mod.ScheduleActionInput(action="nope", delay_seconds=10)
        )


async def test_rejects_meta_actions():
    ctx = _ctx()
    with pytest.raises(ValueError, match="not supported"):
        await schedule_action_handler(
            ctx, sched_mod.ScheduleActionInput(action="schedule_action", delay_seconds=10)
        )


async def test_rejects_dangerous_action():
    ctx = _ctx()
    with pytest.raises(ValueError, match="confirmation"):
        await schedule_action_handler(
            ctx,
            sched_mod.ScheduleActionInput(
                action="purge_messages",
                parameters={"channel_id": "1", "limit": 5},
                delay_seconds=60,
            ),
        )


async def test_rejects_bad_inner_params():
    ctx = _ctx()
    with pytest.raises(ValueError, match="Invalid parameters"):
        await schedule_action_handler(
            ctx, sched_mod.ScheduleActionInput(action="create_channel", delay_seconds=60)
        )


async def test_rejects_bad_cron():
    ctx = _ctx()
    with pytest.raises(ValueError, match="Invalid cron"):
        await schedule_action_handler(
            ctx,
            sched_mod.ScheduleActionInput(
                action="create_channel",
                parameters={"name": "x"},
                cron="not a cron",
            ),
        )


async def test_rejects_bad_timezone():
    ctx = _ctx()
    with pytest.raises(ValueError, match="timezone"):
        await schedule_action_handler(
            ctx,
            sched_mod.ScheduleActionInput(
                action="create_channel",
                parameters={"name": "x"},
                delay_seconds=60,
                timezone="Mars/Olympus",
            ),
        )


# ---------- success paths (mocked DB + scheduler) ----------


def _mock_db(monkeypatch, active_count=0):
    import src.actions.schedules as s

    async def _list(session, guild_id):
        return [MagicMock()] * active_count

    async def _create(**kwargs):
        return SimpleNamespace(id="sched-1")

    async def _update(session, sid, nxt):
        return None

    async def _settings(session, guild_id):
        return SimpleNamespace(maxSchedules=20, timezone="UTC")

    monkeypatch.setattr(s.ScheduledActionRepository, "list_active_for_guild", _list)
    monkeypatch.setattr(s.ScheduledActionRepository, "create_schedule", _create)
    monkeypatch.setattr(s.ScheduledActionRepository, "update_next_run", _update)
    monkeypatch.setattr(s.GuildRepository, "get_settings", _settings)


async def test_schedule_once_success(monkeypatch):
    import src.actions.schedules as s

    _mock_db(monkeypatch)
    calls = {}

    class FakeSched:
        def schedule_saved(self, **kw):
            calls.update(kw)

    monkeypatch.setattr(s, "get_scheduler", lambda: FakeSched())
    out = await schedule_action_handler(
        _ctx(),
        s.ScheduleActionInput(
            action="create_channel", parameters={"name": "lobby"}, delay_seconds=10
        ),
    )
    assert out["schedule_id"] == "sched-1"
    assert out["schedule_type"] == "ONCE"
    assert calls["schedule_id"] == "sched-1"
    assert "run_at" in out


async def test_schedule_cron_success(monkeypatch):
    import src.actions.schedules as s

    _mock_db(monkeypatch)
    calls = {}

    class FakeSched:
        def schedule_saved(self, **kw):
            calls.update(kw)

        def remove_job(self, jid):
            pass

    monkeypatch.setattr(s, "get_scheduler", lambda: FakeSched())
    monkeypatch.setattr(s, "peek_next_run", lambda sid: None)
    out = await schedule_action_handler(
        _ctx(),
        s.ScheduleActionInput(
            action="send_message",
            parameters={"channel_id": "1", "content": "hi"},
            cron="0 9 * * *",
        ),
    )
    assert out["schedule_type"] == "CRON"
    assert calls["cron"] == "0 9 * * *"


async def test_max_schedules_enforced(monkeypatch):
    import src.actions.schedules as s

    _mock_db(monkeypatch, active_count=20)
    with pytest.raises(ValueError, match="already has 20"):
        await schedule_action_handler(
            _ctx(),
            s.ScheduleActionInput(
                action="create_channel", parameters={"name": "x"}, delay_seconds=60
            ),
        )


async def test_cancel_missing(monkeypatch):
    import src.actions.schedules as s

    async def _find(session, sid, gid):
        return None

    monkeypatch.setattr(s.ScheduledActionRepository, "find_by_id", _find)
    with pytest.raises(ValueError, match="not found"):
        await cancel_schedule_handler(_ctx(), s.CancelScheduleInput(schedule_id="missing"))


async def test_cancel_success(monkeypatch):
    import src.actions.schedules as s

    async def _find(session, sid, gid):
        return SimpleNamespace(id=sid)

    async def _disable(session, sid):
        return None

    removed = []
    monkeypatch.setattr(s.ScheduledActionRepository, "find_by_id", _find)
    monkeypatch.setattr(s.ScheduledActionRepository, "disable", _disable)

    class FakeSched:
        def remove_job(self, jid):
            removed.append(jid)

    monkeypatch.setattr(s, "get_scheduler", lambda: FakeSched())
    out = await cancel_schedule_handler(_ctx(), s.CancelScheduleInput(schedule_id="abc"))
    assert out == {"schedule_id": "abc", "cancelled": True}
    assert removed == ["abc"]


async def test_list_schedules(monkeypatch):
    import src.actions.schedules as s

    row = SimpleNamespace(
        id="s1",
        actionPlan={"type": "create_channel", "input": {}},
        scheduleType="CRON",
        cronExpression="0 9 * * *",
        nextRunAt=None,
    )

    async def _list(session, gid):
        return [row]

    monkeypatch.setattr(s.ScheduledActionRepository, "list_active_for_guild", _list)
    out = await list_schedules_handler(_ctx(), s.ListSchedulesInput())
    assert out["schedules"][0]["schedule_id"] == "s1"
    assert "At 09:00" in out["schedules"][0]["when"]
