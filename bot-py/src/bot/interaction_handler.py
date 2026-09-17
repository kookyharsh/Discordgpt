import logging

import discord
from discord.ext import commands

from src.actions.dispatcher import ActionDispatcher
from src.actions.types import ExecutionContext
from src.ai.fallback_parser import FallbackParser
from src.bot.ui import ConfirmationView, DiscordUIComponents
from src.database.repositories import (
    ExecutionRepository,
    GuildRepository,
)
from src.database.session import AsyncSessionLocal
from src.security.injection_defense import InjectionDefense

logger = logging.getLogger("discord_agent")

class BotInteractionHandler:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def handle_prompt(self, interaction: discord.Interaction, request: str):
        # 1. 3s Rule: Always defer public response immediately
        await interaction.response.defer(thinking=True, ephemeral=False)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("Commands can only be executed within a server.", ephemeral=True)
            return

        guild_id = str(guild.id)
        user_id = str(interaction.user.id)
        prompt = InjectionDefense.sanitize_external_text(request)

        if InjectionDefense.detect_prompt_injection(prompt):
            err_embed = DiscordUIComponents.create_error_embed(
                "Security Violation", "Prompt contains suspicious system/injection instructions. Request rejected."
            )
            await interaction.followup.send(embed=err_embed)
            return

        async with AsyncSessionLocal() as session:
            db_guild = await GuildRepository.find_or_create(session, guild_id, guild.name)
            settings = await GuildRepository.get_settings(session, db_guild.id)

            parsed = FallbackParser.parse(prompt)
            if not parsed:
                err_embed = DiscordUIComponents.create_error_embed(
                    "Parsing Required", "Unable to parse request safely."
                )
                await interaction.followup.send(embed=err_embed)
                return

            action_type = parsed.get("action")
            params = parsed.get("parameters", {})

            execution = await ExecutionRepository.create_execution(
                session=session,
                guild_id=db_guild.id,
                user_id=user_id,
                prompt=prompt,
                status="RUNNING",
                parsed_intent=parsed,
            )

            actor_member = interaction.user if isinstance(interaction.user, discord.Member) else await guild.fetch_member(interaction.user.id)

            ctx = ExecutionContext(
                guild_id=db_guild.id,
                user_id=user_id,
                execution_id=execution.id,
                guild=guild,
                actor_member=actor_member,
                settings=settings,
            )

            res = await ActionDispatcher.dispatch(session, action_type, params, ctx)

            if res.requires_confirmation and res.confirmation_details:
                nonce = res.confirmation_details["action_nonce"]
                embed = DiscordUIComponents.create_confirmation_embed(
                    res.confirmation_details["action_type"],
                    res.confirmation_details["risk_level"],
                    str(params),
                    nonce,
                )
                view = ConfirmationView(nonce=nonce, user_id=interaction.user.id)
                await interaction.followup.send(embed=embed, view=view)
                return

            if res.success:
                embed = DiscordUIComponents.create_success_embed("Action Executed", f"Successfully performed **{action_type}**.")
                await interaction.followup.send(embed=embed)
            else:
                embed = DiscordUIComponents.create_error_embed("Action Failed", res.error or "Execution failed.")
                await interaction.followup.send(embed=embed)
