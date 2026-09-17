"""Schedule actions: one-shot delays + cron, DB-backed with live APScheduler jobs.

Side-effect import registers into ActionRegistry.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from pydantic import BaseModel, Field

from src.actions.registry import ActionRegistry
from src.actions.types import ActionDefinition, ConfirmationPolicy, RiskLevel
from src.database.repositories import GuildRepository, ScheduledActionRepository
from src.database.session import AsyncSessionLocal
from src.permissions.permission_engine import PermissionEngine
from src.policies.guild_policy import GuildPolicyEngine
from src.scheduler.scheduler import get_scheduler, peek_next_run

MIN_DELAY_SECONDS = 5
MAX_DELAY_SECONDS = 30 * 86400  # 30 days
DEFAULT_MAX_SCHEDULES = 20
_META_ACTIONS = frozenset({"schedule_action", "list_schedules", "cancel_schedule"})


def _resolve_tz(name: str):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        if (name or "").strip().upper() == "UTC":
            return UTC
        raise ValueError(
            f"Unknown timezone {name!r}. Use an IANA name like 'UTC' or 'America/New_York'."
        ) from None
    except Exception:
        raise ValueError(f"Unknown timezone {name!r}.") from None


def _cron_human(cron: str) -> str | None:
    try:
        from cron_descriptor import get_description

        return get_description(cron)
    except Exception:
        return None


class ScheduleActionInput(BaseModel):
    action: str = Field(..., min_length=1, max_length=64)
    parameters: dict = Field(default_factory=dict)
    delay_seconds: int | None = Field(None, ge=MIN_DELAY_SECONDS, le=MAX_DELAY_SECONDS)
    cron: str | None = Field(None, max_length=128)
    timezone: str = Field("UTC", max_length=64)


async def schedule_action_handler(ctx, data: ScheduleActionInput):
    from apscheduler.triggers.cron import CronTrigger

    if bool(data.delay_seconds) == bool(data.cron):
        raise ValueError("Provide exactly one of delay_seconds or cron.")
    if data.action in _META_ACTIONS:
        raise ValueError("Scheduling a schedule action is not supported.")

    inner_def = ActionRegistry.get(data.action)
    if inner_def is None:
        raise ValueError(f"Unknown action '{data.action}'. Nothing was scheduled.")
    try:
        validated = inner_def.input_schema(**(data.parameters or {}))
    except Exception as e:
        raise ValueError(f"Invalid parameters for '{data.action}': {e}") from None

    # Dangerous actions need a live confirmation click, which a background
    # run can't collect - block them at schedule time with a clear message.
    is_dangerous = inner_def.risk_level.value in ("HIGH", "CRITICAL")
    needs_confirm = inner_def.confirmation_policy.value == "ALWAYS_CONFIRM" or (
        inner_def.confirmation_policy.value == "REQUIRED" and is_dangerous
    )
    if needs_confirm:
        raise ValueError(
            f"'{data.action}' needs your confirmation click, so it can't run "
            "unattended. Run it directly with /prompt instead."
        )

    allowed, policy_reason = GuildPolicyEngine.check_action_allowed(
        data.action, getattr(ctx, "settings", None)
    )
    if not allowed:
        raise ValueError(policy_reason)

    bot_ok, missing_bot = PermissionEngine.check_bot_permissions(
        ctx.guild, inner_def.required_bot_permissions
    )
    if not bot_ok:
        raise ValueError(f"Bot lacks required permission(s): {', '.join(missing_bot)}")
    user_ok, missing_user = PermissionEngine.check_user_permissions(
        ctx.actor_member, inner_def.required_user_permissions
    )
    if not user_ok:
        raise ValueError(f"You lack required permission(s): {', '.join(missing_user)}")

    tz = _resolve_tz(data.timezone)
    now = datetime.now(UTC)
    if data.delay_seconds:
        execute_at = now + timedelta(seconds=data.delay_seconds)
        cron_expr: str | None = None
        schedule_type = "ONCE"
        human = f"in {data.delay_seconds} seconds"
    else:
        try:
            CronTrigger.from_crontab(data.cron or "", timezone=tz)
        except Exception:
            raise ValueError(
                f"Invalid cron expression {data.cron!r}. "
                "Use crontab form like '30 9 * * *' (min hour day month weekday)."
            ) from None
        execute_at = None
        cron_expr = data.cron
        schedule_type = "CRON"
        human = _cron_human(cron_expr or "") or cron_expr
    async with AsyncSessionLocal() as session:
        settings = await GuildRepository.get_settings(session, str(ctx.guild.id))
        max_schedules = getattr(settings, "maxSchedules", None) or DEFAULT_MAX_SCHEDULES
        active = await ScheduledActionRepository.list_active_for_guild(session, str(ctx.guild.id))
        if len(active) >= max_schedules:
            raise ValueError(
                f"This server already has {len(active)} active schedules "
                f"(limit {max_schedules}). Cancel one first."
            )
        sched = await ScheduledActionRepository.create_schedule(
            session=session,
            guild_id=str(ctx.guild.id),
            created_by_user_id=str(ctx.user_id),
            action_plan={"type": data.action, "input": validated.model_dump()},
            schedule_type=schedule_type,
            cron_expression=cron_expr,
            execute_at=execute_at,
            timezone_str=data.timezone,
        )
        sched_id = sched.id
        next_run = execute_at

    get_scheduler().schedule_saved(
        schedule_id=sched_id,
        schedule_type=schedule_type,
        execute_at=execute_at,
        cron=cron_expr,
        timezone_str=data.timezone,
    )

    result: dict = {
        "schedule_id": sched_id,
        "action": data.action,
        "schedule_type": schedule_type,
        "when": human,
    }
    if next_run is not None:
        result["run_at"] = next_run.isoformat()
        async with AsyncSessionLocal() as session:
            await ScheduledActionRepository.update_next_run(session, sched_id, next_run)
    else:
        nxt = peek_next_run(sched_id)
        if nxt is not None:
            result["run_at"] = nxt.isoformat()
            async with AsyncSessionLocal() as session:
                await ScheduledActionRepository.update_next_run(session, sched_id, nxt)
    return result


ActionRegistry.register(
    ActionDefinition(
        type="schedule_action",
        description=(
            "Schedules a Discord action once after delay_seconds (5s-30d) "
            "or on a cron expression. Dangerous actions needing confirmation can't be scheduled."
        ),
        input_schema=ScheduleActionInput,
        required_bot_permissions=discord.Permissions.none(),
        required_user_permissions=discord.Permissions.none(),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=schedule_action_handler,
    )
)


class ListSchedulesInput(BaseModel):
    pass


async def list_schedules_handler(ctx, data: ListSchedulesInput):
    async with AsyncSessionLocal() as session:
        rows = await ScheduledActionRepository.list_active_for_guild(session, str(ctx.guild.id))
    items = []
    for r in rows[:25]:
        plan = r.actionPlan or {}
        when = r.cronExpression or (r.nextRunAt.isoformat() if r.nextRunAt else "?")
        if r.scheduleType == "CRON" and r.cronExpression:
            when = _cron_human(r.cronExpression) or r.cronExpression
        items.append(
            {
                "schedule_id": str(r.id),
                "action": plan.get("type", "?"),
                "schedule_type": r.scheduleType,
                "when": when,
            }
        )
    return {"schedules": items}


ActionRegistry.register(
    ActionDefinition(
        type="list_schedules",
        description="Lists active scheduled (delayed/cron) actions for this server.",
        input_schema=ListSchedulesInput,
        required_bot_permissions=discord.Permissions.none(),
        required_user_permissions=discord.Permissions.none(),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=list_schedules_handler,
    )
)


class CancelScheduleInput(BaseModel):
    schedule_id: str = Field(..., min_length=1, max_length=64)


async def cancel_schedule_handler(ctx, data: CancelScheduleInput):
    async with AsyncSessionLocal() as session:
        found = await ScheduledActionRepository.find_by_id(
            session, data.schedule_id, str(ctx.guild.id)
        )
        if found is None:
            raise ValueError(f"Schedule {data.schedule_id} not found in this server.")
        await ScheduledActionRepository.disable(session, data.schedule_id)

    get_scheduler().remove_job(data.schedule_id)
    return {"schedule_id": data.schedule_id, "cancelled": True}


ActionRegistry.register(
    ActionDefinition(
        type="cancel_schedule",
        description="Cancels a scheduled action by ID.",
        input_schema=CancelScheduleInput,
        required_bot_permissions=discord.Permissions.none(),
        required_user_permissions=discord.Permissions.none(),
        risk_level=RiskLevel.LOW,
        confirmation_policy=ConfirmationPolicy.NOT_REQUIRED,
        handler=cancel_schedule_handler,
    )
)
