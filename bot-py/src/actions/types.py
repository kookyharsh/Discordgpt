from collections.abc import Callable
from enum import Enum
from typing import Any

import discord
from pydantic import BaseModel


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ConfirmationPolicy(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    ALWAYS_CONFIRM = "ALWAYS_CONFIRM"

class ExecutionContext(BaseModel):
    guild_id: str
    user_id: str
    execution_id: str
    guild: Any  # discord.Guild
    actor_member: Any  # discord.Member
    settings: Any | None = None

    class Config:
        arbitrary_types_allowed = True

class ActionDefinition(BaseModel):
    type: str
    description: str
    input_schema: type[BaseModel]
    required_bot_permissions: discord.Permissions
    required_user_permissions: discord.Permissions
    risk_level: RiskLevel
    confirmation_policy: ConfirmationPolicy
    handler: Callable[..., Any]

    class Config:
        arbitrary_types_allowed = True
