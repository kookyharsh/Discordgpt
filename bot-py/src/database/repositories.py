from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    ActionExecution,
    AuditLog,
    ConfirmationRequest,
    Guild,
    GuildSettings,
    ScheduledAction,
)


class GuildRepository:
    @staticmethod
    async def find_or_create(session: AsyncSession, discord_guild_id: str, name: str | None = None) -> Guild:
        stmt = select(Guild).where(Guild.discordGuildId == discord_guild_id)
        result = await session.execute(stmt)
        guild = result.scalar_one_or_none()

        if not guild:
            guild = Guild(discordGuildId=discord_guild_id, name=name)
            session.add(guild)
            await session.flush()

            settings = GuildSettings(guildId=guild.id, timezone="UTC", enabled=True)
            session.add(settings)
            await session.commit()
            await session.refresh(guild)

        return guild

    @staticmethod
    async def get_settings(session: AsyncSession, guild_id: str) -> GuildSettings | None:
        stmt = select(GuildSettings).where(GuildSettings.guildId == guild_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

class ExecutionRepository:
    @staticmethod
    async def create_execution(
        session: AsyncSession,
        guild_id: str,
        user_id: str,
        prompt: str,
        status: str,
        parsed_intent: Any | None = None,
        action_plan: Any | None = None,
    ) -> ActionExecution:
        execution = ActionExecution(
            guildId=guild_id,
            userId=user_id,
            prompt=prompt,
            status=status,
            parsedIntent=parsed_intent,
            actionPlan=action_plan,
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        return execution

class AuditRepository:
    @staticmethod
    async def log(
        session: AsyncSession,
        guild_id: str,
        user_id: str,
        action: str,
        status: str,
        execution_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        parameters: Any | None = None,
        result: Any | None = None,
        error: str | None = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            guildId=guild_id,
            userId=user_id,
            executionId=execution_id,
            action=action,
            targetType=target_type,
            targetId=target_id,
            parameters=parameters,
            result=result,
            status=status,
            error=error,
        )
        session.add(log_entry)
        await session.commit()
        return log_entry

    @staticmethod
    async def get_recent_logs(session: AsyncSession, guild_id: str, limit: int = 20) -> list[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.guildId == guild_id).order_by(AuditLog.createdAt.desc()).limit(limit)
        res = await session.execute(stmt)
        return list(res.scalars().all())

class ConfirmationRepository:
    @staticmethod
    async def create_confirmation(
        session: AsyncSession,
        guild_id: str,
        user_id: str,
        plan_hash: str,
        action_nonce: str,
        action_plan: Any,
        expires_in_seconds: int = 300,
    ) -> ConfirmationRequest:
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        conf = ConfirmationRequest(
            guildId=guild_id,
            userId=user_id,
            planHash=plan_hash,
            actionNonce=action_nonce,
            actionPlan=action_plan,
            expiresAt=expires_at,
        )
        session.add(conf)
        await session.commit()
        return conf

    @staticmethod
    async def find_and_consume(
        session: AsyncSession,
        nonce: str,
        guild_id: str,
        user_id: str,
        expected_hash: str | None = None,
    ) -> ConfirmationRequest | None:
        now = datetime.now(UTC)
        stmt = select(ConfirmationRequest).where(
            ConfirmationRequest.actionNonce == nonce,
            ConfirmationRequest.guildId == guild_id,
            ConfirmationRequest.userId == user_id,
            ConfirmationRequest.consumed == False,
            ConfirmationRequest.expiresAt > now,
        )
        res = await session.execute(stmt)
        conf = res.scalar_one_or_none()

        if not conf:
            return None

        if expected_hash and conf.planHash != expected_hash:
            return None

        conf.consumed = True
        await session.commit()
        return conf

class ScheduledActionRepository:
    @staticmethod
    async def create_schedule(
        session: AsyncSession,
        guild_id: str,
        created_by_user_id: str,
        action_plan: Any,
        schedule_type: str,
        cron_expression: str | None = None,
        execute_at: datetime | None = None,
        timezone_str: str = "UTC",
    ) -> ScheduledAction:
        sched = ScheduledAction(
            guildId=guild_id,
            createdByUserId=created_by_user_id,
            actionPlan=action_plan,
            scheduleType=schedule_type,
            cronExpression=cron_expression,
            executeAt=execute_at,
            timezone=timezone_str,
        )
        session.add(sched)
        await session.commit()
        return sched

    @staticmethod
    async def list_active_for_guild(session: AsyncSession, guild_id: str) -> list[ScheduledAction]:
        stmt = select(ScheduledAction).where(ScheduledAction.guildId == guild_id, ScheduledAction.enabled == True)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_all_active(session: AsyncSession) -> list[ScheduledAction]:
        stmt = select(ScheduledAction).where(ScheduledAction.enabled == True)
        res = await session.execute(stmt)
        return list(res.scalars().all())
