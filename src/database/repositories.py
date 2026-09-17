from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    ActionExecution,
    AuditLog,
    ConfirmationRequest,
    Conversation,
    ConversationMessage,
    Guild,
    GuildSettings,
    PendingChoice,
    PendingQuestion,
    ScheduledAction,
)


class GuildRepository:
    @staticmethod
    async def find_or_create(
        session: AsyncSession, discord_guild_id: str, name: str | None = None
    ) -> Guild:
        stmt = select(Guild).where(Guild.discordGuildId == discord_guild_id)
        result = await session.execute(stmt)
        guild = result.scalar_one_or_none()

        if not guild:
            guild = Guild(discordGuildId=discord_guild_id, name=name)
            session.add(guild)
            await session.flush()

            settings = GuildSettings(guildId=guild.discordGuildId, timezone="UTC", enabled=True)
            session.add(settings)
            await session.commit()
            await session.refresh(guild)

        return guild

    @staticmethod
    async def get_settings(session: AsyncSession, guild_id: str) -> GuildSettings | None:
        stmt = select(GuildSettings).where(GuildSettings.guildId == guild_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_settings(
        session: AsyncSession, guild_id: str, data: dict[str, Any]
    ) -> GuildSettings | None:
        settings = await GuildRepository.get_settings(session, guild_id)
        if not settings:
            return None
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        await session.commit()
        await session.refresh(settings)
        return settings


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
    async def get_recent_logs(
        session: AsyncSession, guild_id: str, limit: int = 20
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.guildId == guild_id)
            .order_by(AuditLog.createdAt.desc())
            .limit(limit)
        )
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
        stmt = select(ScheduledAction).where(
            ScheduledAction.guildId == guild_id, ScheduledAction.enabled == True
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_all_active(session: AsyncSession) -> list[ScheduledAction]:
        stmt = select(ScheduledAction).where(ScheduledAction.enabled == True)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def find_by_id(session: AsyncSession, id: str, guild_id: str) -> ScheduledAction | None:
        stmt = select(ScheduledAction).where(
            ScheduledAction.id == id, ScheduledAction.guildId == guild_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, id: str) -> ScheduledAction | None:
        res = await session.execute(select(ScheduledAction).where(ScheduledAction.id == id))
        return res.scalar_one_or_none()

    @staticmethod
    async def disable(session: AsyncSession, id: str) -> None:
        row = await ScheduledActionRepository.get_by_id(session, id)
        if row is None:
            return
        row.enabled = False
        row.nextRunAt = None
        await session.commit()

    @staticmethod
    async def update_next_run(session: AsyncSession, id: str, next_run: datetime | None) -> None:
        row = await ScheduledActionRepository.get_by_id(session, id)
        if row is None:
            return
        row.nextRunAt = next_run
        await session.commit()

    @staticmethod
    async def record_run(
        session: AsyncSession,
        schedule_id: str,
        status: str,
        result: Any | None = None,
        error: str | None = None,
    ) -> None:
        from src.database.models import ScheduledActionRun

        session.add(
            ScheduledActionRun(
                scheduledActionId=schedule_id, status=status, result=result, error=error
            )
        )
        await session.commit()

    @staticmethod
    async def delete(session: AsyncSession, id: str, guild_id: str) -> int:
        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(ScheduledAction).where(
            ScheduledAction.id == id, ScheduledAction.guildId == guild_id
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount or 0


HISTORY_LIMIT = 10
HISTORY_CHARS = 300


class ConversationRepository:
    @staticmethod
    async def get_or_create(
        session: AsyncSession, guild_id: str, user_id: str, channel_id: str
    ) -> Conversation:
        stmt = (
            select(Conversation)
            .where(
                Conversation.guildId == guild_id,
                Conversation.userId == user_id,
                Conversation.channelId == channel_id,
            )
            .order_by(Conversation.updatedAt.desc())
        )
        res = await session.execute(stmt)
        existing = res.scalars().first()
        if existing:
            return existing
        convo = Conversation(guildId=guild_id, userId=user_id, channelId=channel_id)
        session.add(convo)
        await session.commit()
        await session.refresh(convo)
        return convo

    @staticmethod
    async def append(session: AsyncSession, conversation_id: str, role: str, content: str) -> None:
        from datetime import UTC, datetime

        session.add(
            ConversationMessage(conversationId=conversation_id, role=role, content=content[:2000])
        )
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        res = await session.execute(stmt)
        convo = res.scalar_one_or_none()
        if convo:
            convo.updatedAt = datetime.now(UTC)
        await session.commit()

    @staticmethod
    async def history_lines(
        session: AsyncSession, conversation_id: str, limit: int = HISTORY_LIMIT
    ) -> list[str]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversationId == conversation_id)
            .order_by(ConversationMessage.createdAt.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        rows = list(res.scalars().all())
        return [f"{m.role}: {m.content[:HISTORY_CHARS]}" for m in reversed(rows)]


class PendingQuestionRepository:
    @staticmethod
    async def create(
        session: AsyncSession,
        guild_id: str,
        user_id: str,
        question: str,
        original_prompt: str,
        channel_id: str | None = None,
        expires_in_seconds: int = 900,
    ) -> PendingQuestion:
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        pending = PendingQuestion(
            guildId=guild_id,
            userId=user_id,
            channelId=channel_id,
            question=question[:1000],
            originalPrompt=original_prompt[:2000],
            expiresAt=expires_at,
        )
        session.add(pending)
        await session.commit()
        await session.refresh(pending)
        return pending

    @staticmethod
    async def consume(
        session: AsyncSession, id: str, guild_id: str, user_id: str
    ) -> PendingQuestion | None:
        now = datetime.now(UTC)
        stmt = select(PendingQuestion).where(
            PendingQuestion.id == id,
            PendingQuestion.guildId == guild_id,
            PendingQuestion.userId == user_id,
            PendingQuestion.answered == False,
            PendingQuestion.expiresAt > now,
        )
        res = await session.execute(stmt)
        pending = res.scalar_one_or_none()
        if not pending:
            return None
        pending.answered = True
        await session.commit()
        return pending


class PendingChoiceRepository:
    @staticmethod
    async def create(
        session: AsyncSession,
        guild_id: str,
        user_id: str,
        action: str,
        params: dict[str, Any],
        field: str,
        options: list[dict[str, str]],
        prompt: str,
        expires_in_seconds: int = 300,
    ) -> PendingChoice:
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
        pending = PendingChoice(
            guildId=guild_id,
            userId=user_id,
            action=action,
            params=params,
            field=field,
            options=options,
            prompt=prompt[:2000],
            expiresAt=expires_at,
        )
        session.add(pending)
        await session.commit()
        await session.refresh(pending)
        return pending

    @staticmethod
    async def consume(
        session: AsyncSession, id: str, guild_id: str, user_id: str
    ) -> PendingChoice | None:
        now = datetime.now(UTC)
        stmt = select(PendingChoice).where(
            PendingChoice.id == id,
            PendingChoice.guildId == guild_id,
            PendingChoice.userId == user_id,
            PendingChoice.answered == False,
            PendingChoice.expiresAt > now,
        )
        res = await session.execute(stmt)
        pending = res.scalar_one_or_none()
        if not pending:
            return None
        pending.answered = True
        await session.commit()
        return pending
