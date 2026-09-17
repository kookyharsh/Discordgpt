import logging
from typing import Any

import discord
from pydantic import BaseModel

from src.actions.registry import ActionRegistry
from src.actions.types import ConfirmationPolicy, ExecutionContext, RiskLevel
from src.database.repositories import AuditRepository, ConfirmationRepository
from src.permissions.permission_engine import PermissionEngine
from src.policies.guild_policy import GuildPolicyEngine
from src.security.plan_hasher import PlanHasher
from src.security.tenant_guard import TenantGuard

logger = logging.getLogger("discord_agent.dispatcher")


def friendly_error(action_type: str, err: Exception) -> str:
    """Map technical failures to user-facing hints (full error stays in logs)."""
    raw = str(err) or type(err).__name__
    # Our handlers already raise friendly ValueErrors - pass them through.
    if isinstance(err, ValueError):
        return raw
    if isinstance(err, discord.Forbidden):
        return (
            f"I don't have permission to do '{action_type}'. "
            "Check my role position and Discord permissions, then try again."
        )
    if isinstance(err, discord.NotFound):
        return (
            f"'{action_type}' failed: that channel, member, or message wasn't found. "
            "It may have been deleted - verify the name/ID and try again."
        )
    if isinstance(err, discord.HTTPException):
        return (
            f"Discord rejected '{action_type}' ({raw[:150]}). "
            "Check the inputs (e.g. topic only works on text/forum channels) and try again."
        )
    if isinstance(err, (AttributeError, TypeError)):
        return (
            f"I couldn't complete '{action_type}' due to an internal error. "
            "No changes were made - the team has been notified via logs."
        )
    return f"'{action_type}' failed: {raw[:300]}"


class DispatchResult(BaseModel):
    success: bool
    requires_confirmation: bool = False
    confirmation_details: dict[str, Any] | None = None
    result: Any | None = None
    error: str | None = None


class ActionDispatcher:
    @staticmethod
    async def dispatch(
        session: Any,
        action_type: str,
        parameters: dict[str, Any],
        ctx: ExecutionContext,
    ) -> DispatchResult:
        # 1. Tenant Isolation
        TenantGuard.validate_guild_boundary(ctx.guild_id, str(ctx.guild.id))

        # 2. Whitelist Check
        action_def = ActionRegistry.get(action_type)
        if not action_def:
            return DispatchResult(
                success=False,
                error=f"Unknown or unregistered action type: '{action_type}'. Dynamic code execution is prohibited.",
            )

        # 3. Pydantic Schema Validation
        try:
            validated_input = action_def.input_schema(**parameters)
        except Exception as e:
            return DispatchResult(
                success=False,
                error=f"Invalid parameters for '{action_type}': {e!s}",
            )

        # 4. Guild Policy Check
        allowed, policy_reason = GuildPolicyEngine.check_action_allowed(action_type, ctx.settings)
        if not allowed:
            return DispatchResult(success=False, error=policy_reason)

        # 5. Bot Permissions Check
        bot_ok, missing_bot_perms = PermissionEngine.check_bot_permissions(
            ctx.guild, action_def.required_bot_permissions
        )
        if not bot_ok:
            return DispatchResult(
                success=False,
                error=f"Bot lacks required Discord permission(s): {', '.join(missing_bot_perms)}",
            )

        # 6. User Permissions Check
        user_ok, missing_user_perms = PermissionEngine.check_user_permissions(
            ctx.actor_member, action_def.required_user_permissions
        )
        if not user_ok:
            return DispatchResult(
                success=False,
                error=f"You lack required Discord permission(s): {', '.join(missing_user_perms)}",
            )

        # 7. Risk & Confirmation Gate
        is_dangerous = action_def.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        needs_confirmation = (
            action_def.confirmation_policy == ConfirmationPolicy.ALWAYS_CONFIRM
            or (action_def.confirmation_policy == ConfirmationPolicy.REQUIRED and is_dangerous)
        )

        if needs_confirmation:
            plan = {"type": action_type, "input": validated_input.model_dump()}
            plan_hash = PlanHasher.compute_hash(plan)
            nonce = PlanHasher.generate_nonce()

            await ConfirmationRepository.create_confirmation(
                session=session,
                guild_id=ctx.guild_id,
                user_id=ctx.user_id,
                plan_hash=plan_hash,
                action_nonce=nonce,
                action_plan=plan,
            )

            return DispatchResult(
                success=False,
                requires_confirmation=True,
                confirmation_details={
                    "action_nonce": nonce,
                    "plan_hash": plan_hash,
                    "action_type": action_type,
                    "risk_level": action_def.risk_level.value,
                },
            )

        # 8. Execution
        try:
            res = await action_def.handler(ctx, validated_input)

            await AuditRepository.log(
                session=session,
                guild_id=ctx.guild_id,
                user_id=ctx.user_id,
                action=action_type,
                status="SUCCESS",
                execution_id=ctx.execution_id,
                parameters=validated_input.model_dump(),
                result=res,
            )

            return DispatchResult(success=True, result=res)
        except Exception as err:
            logger.exception("Action '%s' failed", action_type)
            await AuditRepository.log(
                session=session,
                guild_id=ctx.guild_id,
                user_id=ctx.user_id,
                action=action_type,
                status="FAILURE",
                execution_id=ctx.execution_id,
                parameters=validated_input.model_dump(),
                error=str(err),
            )
            return DispatchResult(success=False, error=friendly_error(action_type, err))
