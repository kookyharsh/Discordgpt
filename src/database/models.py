import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Guild(Base):
    __tablename__ = "Guild"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    discordGuildId: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    settings: Mapped[Optional["GuildSettings"]] = relationship(
        "GuildSettings", back_populates="guild", uselist=False, cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="guild", cascade="all, delete-orphan"
    )
    actionExecutions: Mapped[list["ActionExecution"]] = relationship(
        "ActionExecution", back_populates="guild", cascade="all, delete-orphan"
    )
    scheduledActions: Mapped[list["ScheduledAction"]] = relationship(
        "ScheduledAction", back_populates="guild", cascade="all, delete-orphan"
    )
    generatedCommands: Mapped[list["GeneratedCommand"]] = relationship(
        "GeneratedCommand", back_populates="guild", cascade="all, delete-orphan"
    )
    auditLogs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="guild", cascade="all, delete-orphan"
    )
    confirmations: Mapped[list["ConfirmationRequest"]] = relationship(
        "ConfirmationRequest", back_populates="guild", cascade="all, delete-orphan"
    )


class GuildSettings(Base):
    __tablename__ = "GuildSettings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    confirmationMode: Mapped[str] = mapped_column(String, default="STRICT")
    maxSchedules: Mapped[int] = mapped_column(Integer, default=20)
    maxActionsPerMinute: Mapped[int] = mapped_column(Integer, default=60)
    allowedActions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    disabledActions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    auditChannelId: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    guild: Mapped["Guild"] = relationship("Guild", back_populates="settings")


class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    discordUserId: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Conversation(Base):
    __tablename__ = "Conversation"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[str] = mapped_column(String, nullable=False)
    channelId: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    guild: Mapped["Guild"] = relationship("Guild", back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("Conversation_guildId_userId_idx", "guildId", "userId"),)


class ConversationMessage(Base):
    __tablename__ = "ConversationMessage"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    conversationId: Mapped[str] = mapped_column(
        String, ForeignKey("Conversation.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


class ActionExecution(Base):
    __tablename__ = "ActionExecution"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    parsedIntent: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    actionPlan: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    startedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    guild: Mapped["Guild"] = relationship("Guild", back_populates="actionExecutions")
    steps: Mapped[list["ActionExecutionStep"]] = relationship(
        "ActionExecutionStep", back_populates="execution", cascade="all, delete-orphan"
    )
    auditLogs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="execution")

    __table_args__ = (Index("ActionExecution_guildId_userId_idx", "guildId", "userId"),)


class ActionExecutionStep(Base):
    __tablename__ = "ActionExecutionStep"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    executionId: Mapped[str] = mapped_column(
        String, ForeignKey("ActionExecution.id", ondelete="CASCADE"), nullable=False
    )
    stepIndex: Mapped[int] = mapped_column(Integer, nullable=False)
    actionType: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[Any] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    startedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution: Mapped["ActionExecution"] = relationship("ActionExecution", back_populates="steps")


class ScheduledAction(Base):
    __tablename__ = "ScheduledAction"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    createdByUserId: Mapped[str] = mapped_column(String, nullable=False)
    actionPlan: Mapped[Any] = mapped_column(JSONB, nullable=False)
    scheduleType: Mapped[str] = mapped_column(String, nullable=False)
    cronExpression: Mapped[str | None] = mapped_column(String, nullable=True)
    executeAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    nextRunAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    guild: Mapped["Guild"] = relationship("Guild", back_populates="scheduledActions")
    runs: Mapped[list["ScheduledActionRun"]] = relationship(
        "ScheduledActionRun", back_populates="scheduledAction", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ScheduledAction_guildId_enabled_idx", "guildId", "enabled"),)


class ScheduledActionRun(Base):
    __tablename__ = "ScheduledActionRun"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    scheduledActionId: Mapped[str] = mapped_column(
        String, ForeignKey("ScheduledAction.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    executedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    scheduledAction: Mapped["ScheduledAction"] = relationship(
        "ScheduledAction", back_populates="runs"
    )


class GeneratedCommand(Base):
    __tablename__ = "GeneratedCommand"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    createdByUserId: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    actionPlan: Mapped[Any] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    guild: Mapped["Guild"] = relationship("Guild", back_populates="generatedCommands")

    __table_args__ = (
        UniqueConstraint("guildId", "name", name="GeneratedCommand_guildId_name_key"),
    )


class AuditLog(Base):
    __tablename__ = "AuditLog"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[str] = mapped_column(String, nullable=False)
    executionId: Mapped[str | None] = mapped_column(
        String, ForeignKey("ActionExecution.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    targetType: Mapped[str | None] = mapped_column(String, nullable=True)
    targetId: Mapped[str | None] = mapped_column(String, nullable=True)
    parameters: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    guild: Mapped["Guild"] = relationship("Guild", back_populates="auditLogs")
    execution: Mapped[Optional["ActionExecution"]] = relationship(
        "ActionExecution", back_populates="auditLogs"
    )

    __table_args__ = (Index("AuditLog_guildId_createdAt_idx", "guildId", "createdAt"),)


class ConfirmationRequest(Base):
    __tablename__ = "ConfirmationRequest"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[str] = mapped_column(String, nullable=False)
    planHash: Mapped[str] = mapped_column(String, nullable=False)
    actionNonce: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    actionPlan: Mapped[Any] = mapped_column(JSONB, nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    expiresAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    guild: Mapped["Guild"] = relationship("Guild", back_populates="confirmations")

    __table_args__ = (
        Index(
            "ConfirmationRequest_guildId_userId_actionNonce_idx", "guildId", "userId", "actionNonce"
        ),
    )


class PendingQuestion(Base):
    __tablename__ = "PendingQuestion"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[str] = mapped_column(String, nullable=False)
    channelId: Mapped[str | None] = mapped_column(String, nullable=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    originalPrompt: Mapped[str] = mapped_column(Text, nullable=False)
    answered: Mapped[bool] = mapped_column(Boolean, default=False)
    expiresAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("PendingQuestion_guildId_userId_idx", "guildId", "userId"),)


class PendingChoice(Base):
    __tablename__ = "PendingChoice"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    guildId: Mapped[str] = mapped_column(
        String, ForeignKey("Guild.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    params: Mapped[Any] = mapped_column(JSONB, nullable=False)
    field: Mapped[str] = mapped_column(String, nullable=False)
    options: Mapped[Any] = mapped_column(JSONB, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    answered: Mapped[bool] = mapped_column(Boolean, default=False)
    expiresAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("PendingChoice_guildId_userId_idx", "guildId", "userId"),)


class RateLimitState(Base):
    __tablename__ = "RateLimitState"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    expireAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
