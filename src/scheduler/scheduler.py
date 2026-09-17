"""APScheduler wiring for delayed + cron Discord actions.

Jobs are persisted in the ScheduledAction table and re-registered on
startup, so schedules survive bot restarts. Every run re-checks guild
policy and bot permissions before executing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger("discord_agent_scheduler")

_instance: AgentScheduler | None = None
_bot = None
_restored = False


def _resolve_tz(name: str):
    try:
        return ZoneInfo(name or "UTC")
    except Exception:
        if (name or "").strip().upper() == "UTC":
            return UTC
        raise


class AgentScheduler:
    def __init__(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self.scheduler = AsyncIOScheduler()

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler shut down.")

    def add_cron_job(
        self,
        job_id: str,
        func=None,
        cron_expression: str | None = None,
        args: list | None = None,
        kwargs: dict | None = None,
        timezone_str: str = "UTC",
    ):
        """Register (or replace) a cron job. Defaults to executing a saved schedule."""
        from apscheduler.triggers.cron import CronTrigger

        if cron_expression is None:
            raise ValueError("cron_expression is required.")
        trigger = CronTrigger.from_crontab(cron_expression, timezone=_resolve_tz(timezone_str))
        self.scheduler.add_job(
            func or execute_scheduled_job,
            trigger=trigger,
            id=job_id,
            args=args if args is not None else [job_id],
            kwargs=kwargs or {},
            replace_existing=True,
        )

    def add_once_job(
        self,
        job_id: str,
        run_at: datetime,
        timezone_str: str = "UTC",
    ):
        from apscheduler.triggers.date import DateTrigger

        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=UTC)
        trigger = DateTrigger(run_date=run_at, timezone=_resolve_tz(timezone_str))
        self.scheduler.add_job(
            execute_scheduled_job,
            trigger=trigger,
            id=job_id,
            args=[job_id],
            replace_existing=True,
        )

    def schedule_saved(
        self,
        schedule_id: str,
        schedule_type: str,
        execute_at: datetime | None,
        cron: str | None,
        timezone_str: str = "UTC",
    ):
        if schedule_type == "ONCE":
            if execute_at is None:
                raise ValueError("ONCE schedules need execute_at.")
            self.add_once_job(schedule_id, execute_at, timezone_str)
        else:
            self.add_cron_job(schedule_id, None, cron, None, None, timezone_str)

    def remove_job(self, job_id: str) -> None:
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass


def get_scheduler() -> AgentScheduler:
    global _instance
    if _instance is None:
        _instance = AgentScheduler()
    return _instance


def set_bot(bot) -> None:
    global _bot
    _bot = bot


def reset_scheduler_state() -> None:
    """Test hook: drop the singleton/bot/restored flag."""
    global _instance, _bot, _restored
    try:
        if _instance is not None and _instance.scheduler.running:
            _instance.scheduler.shutdown(wait=False)
    except Exception:
        pass
    _instance = None
    _bot = None
    _restored = False


def peek_next_run(schedule_id: str) -> datetime | None:
    try:
        job = get_scheduler().scheduler.get_job(schedule_id)
    except Exception:
        return None
    return getattr(job, "next_run_time", None)


async def restore_all() -> int:
    """Re-register every enabled DB schedule. Idempotent; needs the bot for later runs."""
    global _restored
    from src.database.repositories import ScheduledActionRepository
    from src.database.session import AsyncSessionLocal

    sched = get_scheduler()
    sched.start()
    count = 0
    try:
        async with AsyncSessionLocal() as session:
            rows = await ScheduledActionRepository.list_all_active(session)
    except Exception as e:
        logger.warning("Scheduler restore skipped (DB unavailable): %s", e)
        return 0
    for row in rows:
        try:
            sched.schedule_saved(
                schedule_id=str(row.id),
                schedule_type=row.scheduleType,
                execute_at=row.executeAt,
                cron=row.cronExpression,
                timezone_str=row.timezone or "UTC",
            )
            try:
                nxt = peek_next_run(str(row.id))
                if nxt is not None:
                    async with AsyncSessionLocal() as session:
                        await ScheduledActionRepository.update_next_run(session, str(row.id), nxt)
            except Exception:
                pass
            count += 1
        except Exception as e:
            logger.warning("Skipping unparsable schedule %s: %s", row.id, e)
    _restored = True
    if count:
        logger.info("Restored %d scheduled action(s).", count)
    return count


async def execute_scheduled_job(schedule_id: str) -> None:
    """APScheduler target: load the row, re-check policy/perms, dispatch."""
    from src.actions.dispatcher import ActionDispatcher
    from src.actions.registry import ActionRegistry
    from src.actions.types import ExecutionContext
    from src.database.repositories import (
        GuildRepository,
        ScheduledActionRepository,
    )
    from src.database.session import AsyncSessionLocal
    from src.policies.guild_policy import GuildPolicyEngine

    try:
        async with AsyncSessionLocal() as session:
            row = await ScheduledActionRepository.get_by_id(session, schedule_id)
    except Exception as e:
        logger.warning("Scheduled job %s: DB unavailable, will retry: %s", schedule_id, e)
        return
    if row is None or not row.enabled:
        get_scheduler().remove_job(schedule_id)
        return

    guild_id = row.guildId
    plan: dict[str, Any] = dict(row.actionPlan or {})
    action_type = plan.get("type", "")
    parameters: dict[str, Any] = dict(plan.get("input") or {})

    if _bot is None:
        logger.warning("Scheduled job %s: bot not connected, skipping run.", schedule_id)
        return
    try:
        guild = _bot.get_guild(int(guild_id))
        if guild is None:
            guild = await _bot.fetch_guild(int(guild_id))
    except Exception as e:
        logger.warning("Scheduled job %s: guild %s unreachable: %s", schedule_id, guild_id, e)
        return

    action_def = ActionRegistry.get(action_type)
    if action_def is None:
        await _finish_run(
            schedule_id,
            row.scheduleType,
            "SKIPPED",
            None,
            f"Action '{action_type}' is no longer registered.",
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            settings = await GuildRepository.get_settings(session, guild_id)
    except Exception:
        settings = None

    allowed, reason = GuildPolicyEngine.check_action_allowed(action_type, settings)
    if not allowed:
        await _finish_run(schedule_id, row.scheduleType, "SKIPPED", None, reason)
        return

    # Re-resolve the actor: original requester if still in guild, else the bot.
    actor = None
    try:
        actor = guild.get_member(int(row.createdByUserId))
        if actor is None:
            actor = await guild.fetch_member(int(row.createdByUserId))
    except Exception:
        actor = None
    if actor is None:
        actor = guild.me

    ctx = ExecutionContext(
        guild_id=guild_id,
        user_id=str(row.createdByUserId),
        execution_id=f"sched-{schedule_id}-{datetime.now(UTC).isoformat()}",
        guild=guild,
        actor_member=actor,
        settings=settings,
    )
    try:
        async with AsyncSessionLocal() as session:
            res = await ActionDispatcher.dispatch(session, action_type, parameters, ctx)
    except Exception as e:
        logger.exception("Scheduled job %s crashed", schedule_id)
        await _finish_run(schedule_id, row.scheduleType, "FAILURE", None, str(e))
        return

    if res.requires_confirmation:
        await _finish_run(
            schedule_id,
            row.scheduleType,
            "SKIPPED",
            None,
            "Action needs manual confirmation; unschedule or run it directly.",
        )
        return
    if res.success:
        logger.info("Scheduled job %s ran %s successfully.", schedule_id, action_type)
        await _finish_run(schedule_id, row.scheduleType, "SUCCESS", res.result, None)
    else:
        logger.warning("Scheduled job %s failed: %s", schedule_id, res.error)
        await _finish_run(schedule_id, row.scheduleType, "FAILURE", None, res.error)


async def _finish_run(
    schedule_id: str, schedule_type: str, status: str, result: Any | None, error: str | None
) -> None:
    from src.database.repositories import ScheduledActionRepository
    from src.database.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await ScheduledActionRepository.record_run(session, schedule_id, status, result, error)
            if schedule_type == "ONCE" and status in ("SUCCESS", "FAILURE", "SKIPPED"):
                await ScheduledActionRepository.disable(session, schedule_id)
    except Exception as e:
        logger.warning("Could not record run for %s: %s", schedule_id, e)
    if schedule_type == "ONCE":
        get_scheduler().remove_job(schedule_id)
    else:
        try:
            nxt = peek_next_run(schedule_id)
            async with AsyncSessionLocal() as session:
                await ScheduledActionRepository.update_next_run(session, schedule_id, nxt)
        except Exception:
            pass
