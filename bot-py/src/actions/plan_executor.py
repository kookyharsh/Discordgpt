from __future__ import annotations

from typing import Any

from src.actions.dispatcher import ActionDispatcher
from src.actions.types import ExecutionContext
from src.database.repositories import ConfirmationRepository
from src.entities.entity_resolver import EntityResolver
from src.security.plan_hasher import PlanHasher

MAX_PLAN_STEPS = 5
PLAN_TYPE = "__plan__"


def summarize_plan(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No steps were executed."
    ok = sum(1 for r in results if r.get("ok"))
    lines = [
        f"✓ {r['action']}"
        if r.get("ok")
        else f"✗ {r['action']}: {(r.get('error') or 'failed')[:120]}"
        for r in results
    ]
    return f"{ok}/{len(results)} steps succeeded.\n" + "\n".join(lines)


async def execute_action_plan(
    session: Any,
    steps: list[dict[str, Any]],
    start_index: int,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute plan steps in order with the full safety pipeline per step.

    Name-based params (channelName/channel_name/roleName/role_name) resolve
    per step. On a confirmation gate the REMAINDER is stashed and a
    confirmation dict is returned; resume with start_index=i after approval.
    """
    results: list[dict[str, Any]] = []

    for i in range(start_index, len(steps)):
        step = steps[i]
        action = step.get("action", "")
        params: dict[str, Any] = dict(step.get("parameters") or {})

        channel_name = params.get("channelName") or params.get("channel_name")
        if channel_name and not params.get("channel_id"):
            res = await EntityResolver.resolve_channel(ctx.guild, str(channel_name))
            if res.resolved is not None:
                params["channel_id"] = str(res.resolved.id)
        role_name = params.get("roleName") or params.get("role_name")
        if role_name and not params.get("role_id"):
            res = await EntityResolver.resolve_role(ctx.guild, str(role_name))
            if res.resolved is not None:
                params["role_id"] = str(res.resolved.id)

        dispatch_res = await ActionDispatcher.dispatch(session, action, params, ctx)

        if dispatch_res.requires_confirmation and dispatch_res.confirmation_details:
            plan = {"type": PLAN_TYPE, "steps": steps, "index": i}
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
            return {
                "completed": False,
                "results": results,
                "confirmation": {
                    "nonce": nonce,
                    "action_type": action,
                    "risk_level": dispatch_res.confirmation_details.get("risk_level", "HIGH"),
                    "step_label": f"{i + 1}/{len(steps)}",
                },
            }

        results.append(
            {
                "step_id": step.get("id", str(i)),
                "action": action,
                "ok": dispatch_res.success,
                "result": dispatch_res.result,
                "error": dispatch_res.error,
            }
        )
        if not dispatch_res.success:
            return {"completed": True, "results": results}

    return {"completed": True, "results": results}
