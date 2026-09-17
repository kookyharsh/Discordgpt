from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord
from discord.ext import commands

from src.actions.dispatcher import ActionDispatcher
from src.actions.plan_executor import MAX_PLAN_STEPS, PLAN_TYPE, execute_action_plan, summarize_plan
from src.actions.registry import ActionRegistry
from src.actions.types import ExecutionContext
from src.ai.fallback_parser import FallbackParser
from src.bot.ui import (
    ClarifyModal,
    ConfirmationView,
    DisambiguationView,
    DiscordUIComponents,
)
from src.database.repositories import (
    ConfirmationRepository,
    ConversationRepository,
    ExecutionRepository,
    GuildRepository,
    PendingChoiceRepository,
    PendingQuestionRepository,
)
from src.database.session import AsyncSessionLocal
from src.security.injection_defense import InjectionDefense

logger = logging.getLogger("discord_agent")

CHANNEL_ACTIONS = {
    "send_message",
    "purge_messages",
    "set_slowmode",
    "lock_channel",
    "unlock_channel",
    "rename_channel",
    "set_topic",
    "pin_message",
    "unpin_message",
    "delete_channel",
    "edit_channel",
}


class BotInteractionHandler:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- entry ----------

    async def handle_prompt(self, interaction: discord.Interaction, request: str):
        await interaction.response.defer(thinking=True, ephemeral=False)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send(
                "Commands can only be executed within a server.", ephemeral=True
            )
            return

        guild_id = str(guild.id)
        user_id = str(interaction.user.id)
        prompt = InjectionDefense.sanitize_external_text(request)

        if InjectionDefense.detect_prompt_injection(prompt):
            await interaction.followup.send(
                embed=DiscordUIComponents.create_error_embed(
                    "Security Violation",
                    "Prompt contains suspicious system/injection instructions. Request rejected.",
                )
            )
            return

        async with AsyncSessionLocal() as session:
            # Upsert side effect only: the canonical tenant key is the
            # Discord snowflake (guild_id), matching the legacy FK targets.
            await GuildRepository.find_or_create(session, guild_id, guild.name)
            settings = await GuildRepository.get_settings(session, guild_id)
            channel_id = str(getattr(interaction, "channel_id", None) or guild_id)
            convo = await ConversationRepository.get_or_create(
                session, guild_id, user_id, channel_id
            )
            history = await ConversationRepository.history_lines(session, convo.id)

            parsed = FallbackParser.parse(prompt)
            source = "fallback"
            if parsed is None:
                from src.ai.needle_agent import parse_with_needle

                now = datetime.now(UTC).strftime("%Y-%m-%d %a %H:%M")
                channels = [{"id": str(c.id), "name": c.name} for c in guild.channels[:100]]
                roles = [{"id": str(r.id), "name": r.name} for r in guild.roles[:100]]
                allowed = None
                if settings is not None:
                    allow = getattr(settings, "allowedActions", None) or []
                    if allow:
                        allowed = list(allow)
                system = (
                    f"date: {now}; locale: en-US; channels: {len(channels)}; roles: {len(roles)}"
                )
                if history:
                    system += "; history: " + " | ".join(history[-6:])
                parsed = parse_with_needle(prompt, allowed_actions=allowed, system=system)
                source = "needle"
                logger.info("prompt parsed via=%s status=%s", source, parsed.get("status"))

            status = parsed.get(
                "status", "direct_action" if parsed.get("action") else "unsupported"
            )

            if status in ("unsupported", "rejected"):
                reason = parsed.get("reason", "This request is unsupported.")
                await interaction.followup.send(
                    embed=DiscordUIComponents.create_error_embed("Operation Rejected", reason)
                )
                await ConversationRepository.append(session, convo.id, "user", prompt)
                await ConversationRepository.append(
                    session, convo.id, "assistant", f"I couldn't do that: {reason[:300]}"
                )
                return

            if status == "chat":
                text = str(parsed.get("message", "")).strip()[:1900] or "How can I help?"
                await interaction.followup.send(text)
                await ConversationRepository.append(session, convo.id, "user", prompt)
                await ConversationRepository.append(session, convo.id, "assistant", text[:500])
                return

            if status == "clarification_required":
                question = str(parsed.get("question") or "Please provide more details.")[:500]
                pending = await PendingQuestionRepository.create(
                    session,
                    guild_id=guild_id,
                    user_id=user_id,
                    question=question,
                    original_prompt=prompt,
                    channel_id=channel_id,
                )
                embed = DiscordUIComponents.create_question_embed(question)
                view = discord.ui.View(timeout=900)
                answer_btn = discord.ui.Button(label="Answer", style=discord.ButtonStyle.primary)

                async def _ask(itx: discord.Interaction):
                    await itx.response.send_modal(
                        ClarifyModal(
                            title="Additional detail",
                            on_submit_cb=lambda m_itx, ans: self._resume_after_answer(
                                m_itx, pending.id, ans
                            ),
                        )
                    )

                answer_btn.callback = _ask  # type: ignore[method-assign]
                view.add_item(answer_btn)
                await interaction.followup.send(embed=embed, view=view)
                await ConversationRepository.append(session, convo.id, "user", prompt)
                await ConversationRepository.append(
                    session, convo.id, "assistant", f"I asked: {question[:300]}"
                )
                return

            if status == "action_plan":
                steps = parsed.get("steps") or []
                if len(steps) > MAX_PLAN_STEPS:
                    msg = (
                        f"That plan has {len(steps)} steps; I execute at most {MAX_PLAN_STEPS}. "
                        "Break it into smaller requests."
                    )
                    await interaction.followup.send(
                        embed=DiscordUIComponents.create_error_embed("Plan Too Large", msg)
                    )
                    return
                await self._run_plan(
                    interaction,
                    session,
                    guild,
                    guild_id,
                    user_id,
                    prompt,
                    convo.id,
                    steps,
                    settings,
                )
                return

            # direct_action (fallback shape {"action", "parameters"} or needle shape)
            action_type = parsed.get("action", "")
            params = dict(parsed.get("parameters") or {})
            if not action_type:
                await interaction.followup.send(
                    embed=DiscordUIComponents.create_error_embed(
                        "Operation Rejected", "No executable action found. Try rephrasing."
                    )
                )
                return
            await self._execute_single_action(
                interaction,
                session,
                guild,
                guild_id,
                user_id,
                prompt,
                convo.id,
                action_type,
                params,
                settings,
                channel_id,
            )

    # ---------- single action ----------

    async def _execute_single_action(
        self,
        interaction,
        session,
        guild,
        tenant_id,
        user_id,
        prompt,
        convo_id,
        action_type,
        params,
        settings,
        default_channel_id,
    ):
        from src.entities.entity_resolver import EntityResolver

        # Channel name -> id
        if params.get("channel_name") and not params.get("channel_id"):
            res = await EntityResolver.resolve_channel(guild, str(params["channel_name"]))
            if res.resolved is not None:
                params["channel_id"] = str(res.resolved.id)
            elif res.ambiguous and res.matches:
                await self._ask_disambiguation(
                    interaction,
                    session,
                    guild,
                    tenant_id,
                    user_id,
                    prompt,
                    convo_id,
                    action_type,
                    params,
                    "channel_id",
                    [{"id": str(c.id), "name": f"#{c.name}"} for c in res.matches[:10]],
                    "channel",
                    default_channel_id,
                    settings,
                )
                return
            else:
                msg = f'I couldn\'t find a channel named "{params["channel_name"]}". Check the name and try again.'
                await self._reply_error(
                    interaction, session, convo_id, prompt, "Channel Not Found", msg
                )
                return

        if params.get("role_name") and not params.get("role_id"):
            res = await EntityResolver.resolve_role(guild, str(params["role_name"]))
            if res.resolved is not None:
                params["role_id"] = str(res.resolved.id)
            elif res.ambiguous and res.matches:
                await self._ask_disambiguation(
                    interaction,
                    session,
                    guild,
                    tenant_id,
                    user_id,
                    prompt,
                    convo_id,
                    action_type,
                    params,
                    "role_id",
                    [{"id": str(r.id), "name": f"@{r.name}"} for r in res.matches[:10]],
                    "role",
                    default_channel_id,
                    settings,
                )
                return
            else:
                msg = f'I couldn\'t find a role named "{params["role_name"]}". Check the name and try again.'
                await self._reply_error(
                    interaction, session, convo_id, prompt, "Role Not Found", msg
                )
                return

        if not params.get("channel_id") and action_type in CHANNEL_ACTIONS and default_channel_id:
            params["channel_id"] = default_channel_id

        execution = await ExecutionRepository.create_execution(
            session=session,
            guild_id=tenant_id,
            user_id=user_id,
            prompt=prompt,
            status="RUNNING",
            parsed_intent={"action": action_type, "parameters": params},
        )
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            try:
                actor = await guild.fetch_member(interaction.user.id)
            except Exception:
                pass
        ctx = ExecutionContext(
            guild_id=tenant_id,
            user_id=user_id,
            execution_id=execution.id,
            guild=guild,
            actor_member=actor,
            settings=settings,
        )
        res = await ActionDispatcher.dispatch(session, action_type, params, ctx)

        if res.requires_confirmation and res.confirmation_details:
            nonce = res.confirmation_details["action_nonce"]
            embed = DiscordUIComponents.create_confirmation_embed(
                res.confirmation_details["action_type"],
                res.confirmation_details["risk_level"],
                str(params)[:1500],
                nonce,
            )
            view = ConfirmationView(
                nonce=nonce,
                user_id=interaction.user.id,
                on_confirm=lambda itx: self._handle_confirm(itx, nonce),
            )
            await interaction.followup.send(embed=embed, view=view)
            await ConversationRepository.append(
                session,
                convo_id,
                "assistant",
                f"I asked for confirmation before doing {action_type}.",
            )
            return

        if res.success:
            detail = f"\n`{str(res.result)[:300]}`" if res.result else ""
            await interaction.followup.send(
                embed=DiscordUIComponents.create_success_embed(
                    "Action Executed", f"Successfully performed **{action_type}**.{detail}"
                )
            )
            await ConversationRepository.append(session, convo_id, "user", prompt)
            await ConversationRepository.append(
                session, convo_id, "assistant", f"I did {action_type} successfully."
            )
        else:
            await self._reply_error(
                interaction,
                session,
                convo_id,
                prompt,
                "Action Failed",
                res.error or "Execution failed.",
            )

    async def _run_plan(
        self, interaction, session, guild, tenant_id, user_id, prompt, convo_id, steps, settings
    ):
        execution = await ExecutionRepository.create_execution(
            session=session,
            guild_id=tenant_id,
            user_id=user_id,
            prompt=prompt,
            status="RUNNING",
            parsed_intent={"status": "action_plan", "steps": steps},
        )
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            try:
                actor = await guild.fetch_member(interaction.user.id)
            except Exception:
                pass
        ctx = ExecutionContext(
            guild_id=tenant_id,
            user_id=user_id,
            execution_id=execution.id,
            guild=guild,
            actor_member=actor,
            settings=settings,
        )
        plan_res = await execute_action_plan(session, steps, 0, ctx)
        if not plan_res.get("completed") and plan_res.get("confirmation"):
            c = plan_res["confirmation"]
            embed = DiscordUIComponents.create_confirmation_embed(
                c["action_type"],
                c["risk_level"],
                f"Plan step {c['step_label']} needs approval.\n{summarize_plan(plan_res['results'])}",
                c["nonce"],
            )
            view = ConfirmationView(
                nonce=c["nonce"],
                user_id=interaction.user.id,
                on_confirm=lambda itx: self._handle_confirm(itx, c["nonce"]),
            )
            await interaction.followup.send(embed=embed, view=view)
            return
        summary = summarize_plan(plan_res["results"])
        all_ok = bool(plan_res["results"]) and all(r.get("ok") for r in plan_res["results"])
        await interaction.followup.send(
            embed=(
                DiscordUIComponents.create_success_embed("Plan Executed", summary)
                if all_ok
                else DiscordUIComponents.create_error_embed("Plan Had Failures", summary)
            )
        )
        await ConversationRepository.append(session, convo_id, "user", prompt)
        await ConversationRepository.append(session, convo_id, "assistant", summary[:500])

    # ---------- helpers ----------

    async def _reply_error(self, interaction, session, convo_id, prompt, title, msg):
        await interaction.followup.send(embed=DiscordUIComponents.create_error_embed(title, msg))
        try:
            await ConversationRepository.append(session, convo_id, "user", prompt)
            await ConversationRepository.append(
                session, convo_id, "assistant", f"That failed: {msg[:300]}"
            )
        except Exception:
            pass

    async def _ask_disambiguation(
        self,
        interaction,
        session,
        guild,
        tenant_id,
        user_id,
        prompt,
        convo_id,
        action_type,
        params,
        field,
        options,
        kind,
        default_channel_id,
        settings,
    ):
        pending = await PendingChoiceRepository.create(
            session,
            guild_id=tenant_id,
            user_id=user_id,
            action=action_type,
            params=params,
            field=field,
            options=options,
            prompt=prompt,
        )
        embed = DiscordUIComponents.create_disambiguation_embed(
            f"Which {kind}?",
            f"I found {len(options)} matching {kind}s. Pick one below (expires in 5 minutes).",
        )

        async def _picked(itx: discord.Interaction, chosen: str):
            async with AsyncSessionLocal() as s2:
                claimed = await PendingChoiceRepository.consume(s2, pending.id, tenant_id, user_id)
                if claimed is None:
                    await itx.response.send_message(
                        "Selection expired. Run /prompt again.", ephemeral=True
                    )
                    return
                valid_ids = {(o.get("id")) for o in (claimed.options or [])}
                if chosen not in valid_ids:
                    await itx.response.send_message("Invalid selection.", ephemeral=True)
                    return
                await itx.response.defer()
                await self._execute_single_action(
                    itx,
                    s2,
                    guild,
                    tenant_id,
                    user_id,
                    prompt,
                    convo_id,
                    claimed.action,
                    {**(claimed.params or {}), claimed.field: chosen},
                    settings,
                    default_channel_id,
                )

        view = DisambiguationView(options=options, user_id=interaction.user.id, on_pick=_picked)
        await interaction.followup.send(embed=embed, view=view)

    async def _resume_after_answer(
        self, interaction: discord.Interaction, pending_id: str, answer: str
    ):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Follow-ups only work within a server.", ephemeral=True)
            return
        guild_id = str(guild.id)
        user_id = str(interaction.user.id)
        async with AsyncSessionLocal() as session:
            await GuildRepository.find_or_create(session, guild_id, guild.name)
            pending = await PendingQuestionRepository.consume(
                session, pending_id, guild_id, user_id
            )
            if pending is None:
                await interaction.followup.send(
                    embed=DiscordUIComponents.create_error_embed(
                        "Answer Expired",
                        "This question already expired or belongs to someone else. Run /prompt again.",
                    )
                )
                return
            combined = f"{pending.originalPrompt}\nAdditional detail from user: {answer}"
            # Re-enter the flow as a fresh prompt turn.
            await self.handle_prompt(interaction, combined)

    async def _handle_confirm(self, interaction: discord.Interaction, nonce: str):
        await interaction.response.defer()
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send(
                "Confirmations only work within a server.", ephemeral=True
            )
            return
        guild_id = str(guild.id)
        user_id = str(interaction.user.id)
        async with AsyncSessionLocal() as session:
            await GuildRepository.find_or_create(session, guild_id, guild.name)
            conf = await ConfirmationRepository.find_and_consume(
                session, nonce=nonce, guild_id=guild_id, user_id=user_id
            )
            if conf is None:
                await interaction.followup.send(
                    embed=DiscordUIComponents.create_error_embed(
                        "Invalid or Expired Confirmation",
                        "This confirmation expired, was consumed, or belongs to another user.",
                    )
                )
                return
            plan = conf.actionPlan or {}
            try:
                actor = interaction.user
                if not isinstance(actor, discord.Member):
                    actor = await guild.fetch_member(interaction.user.id)
                settings = await GuildRepository.get_settings(session, guild_id)
                ctx = ExecutionContext(
                    guild_id=guild_id,
                    user_id=user_id,
                    execution_id=f"conf-{nonce}",
                    guild=guild,
                    actor_member=actor,
                    settings=settings,
                )
                if plan.get("type") == PLAN_TYPE and isinstance(plan.get("steps"), list):
                    plan_res = await execute_action_plan(
                        session, plan["steps"], int(plan.get("index", 0)), ctx
                    )
                    if not plan_res.get("completed") and plan_res.get("confirmation"):
                        c = plan_res["confirmation"]
                        embed = DiscordUIComponents.create_confirmation_embed(
                            c["action_type"],
                            c["risk_level"],
                            f"Plan step {c['step_label']} needs approval.\n{summarize_plan(plan_res['results'])}",
                            c["nonce"],
                        )
                        view = ConfirmationView(
                            nonce=c["nonce"],
                            user_id=interaction.user.id,
                            on_confirm=lambda itx: self._handle_confirm(itx, c["nonce"]),
                        )
                        await interaction.followup.send(embed=embed, view=view)
                        return
                    summary = summarize_plan(plan_res["results"])
                    all_ok = bool(plan_res["results"]) and all(
                        r.get("ok") for r in plan_res["results"]
                    )
                    await interaction.followup.send(
                        embed=(
                            DiscordUIComponents.create_success_embed("Plan Executed", summary)
                            if all_ok
                            else DiscordUIComponents.create_error_embed(
                                "Plan Had Failures", summary
                            )
                        )
                    )
                    return
                action_def = ActionRegistry.get(plan.get("type", ""))
                if action_def is None:
                    await interaction.followup.send(
                        embed=DiscordUIComponents.create_error_embed(
                            "Execution Failed", "Action definition no longer exists."
                        )
                    )
                    return
                result = await action_def.handler(
                    ctx, action_def.input_schema(**(plan.get("input") or {}))
                )
                await interaction.followup.send(
                    embed=DiscordUIComponents.create_success_embed(
                        "Action Executed",
                        f"Successfully executed confirmed operation **{plan.get('type')}**.\n`{str(result)[:300]}`",
                    )
                )
            except Exception as err:
                await interaction.followup.send(
                    embed=DiscordUIComponents.create_error_embed("Execution Failed", str(err)[:500])
                )
