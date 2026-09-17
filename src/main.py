import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

import discord
import uvicorn
from discord.ext import commands

from src.ai.needle_agent import check_artifacts_stale
from src.api.server import app as fastapi_app
from src.bot.interaction_handler import BotInteractionHandler
from src.bot.logger import (
    log_api_only_mode,
    log_bot_ready,
    log_startup_checklist,
    log_sync_failed,
    log_sync_result,
    print_startup_banner,
    setup_colored_logging,
)

logger = setup_colored_logging("discord_agent_main")

intents = discord.Intents.none()
intents.guilds = True
# Members intent powers username/nickname search (resolve_member) and the
# member cache. ALSO toggle "Server Members Intent" in the Discord dev portal
# (Bot tab); without it, name search sees almost nobody and only @mentions/IDs work.
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
handler = BotInteractionHandler(bot)


@bot.event
async def on_ready():
    logger.info("Bot connected as %s (ID: %s)", bot.user, getattr(bot.user, "id", "?"))
    try:
        guild_count = len(bot.guilds) if hasattr(bot, "guilds") else None
    except Exception:
        guild_count = None
    log_bot_ready(bot.user, guild_count)
    try:
        from src.scheduler.scheduler import restore_all

        restored = await restore_all()
        if restored:
            logger.info("Restored %d scheduled action(s) from the database.", restored)
    except Exception as e:
        logger.warning("Schedule restore failed: %s", e)
    try:
        synced = await bot.tree.sync()
        logger.info("Synced %d slash commands.", len(synced))
        log_sync_result(len(synced))
    except Exception as e:
        logger.exception("Failed to sync commands")
        log_sync_failed(e)


@bot.tree.command(
    name="prompt", description="Execute Discord management actions using natural language"
)
async def prompt_slash(interaction: discord.Interaction, request: str):
    await handler.handle_prompt(interaction, request)


@bot.tree.command(name="prompt-audit", description="View recent bot management action audit logs")
async def prompt_audit_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    if interaction.guild is None:
        await interaction.followup.send(
            "Commands can only be used within a server.", ephemeral=True
        )
        return
    from src.database.repositories import AuditRepository, GuildRepository
    from src.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        guild_key = str(interaction.guild.id)
        await GuildRepository.find_or_create(session, guild_key, interaction.guild.name)
        logs = await AuditRepository.get_recent_logs(session, guild_key, 10)
    lines = [
        f"• [{l.createdAt.isoformat()}] **{l.action}** by <@{l.userId}>: {l.status}" for l in logs
    ]
    from src.bot.ui import DiscordUIComponents

    await interaction.followup.send(
        embed=DiscordUIComponents.create_success_embed(
            "Recent Audit Logs", "\n".join(lines) or "No audit logs found."
        ),
        ephemeral=True,
    )


@bot.tree.command(
    name="prompt-help", description="Display documentation and supported actions catalog"
)
async def prompt_help_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    from src.actions.registry import ActionRegistry
    from src.bot.ui import DiscordUIComponents

    catalog = "\n".join(f"• **{a.type}** — {a.description}" for a in ActionRegistry.get_all())
    await interaction.followup.send(
        embed=DiscordUIComponents.create_success_embed(
            "Natural Language Bot Help",
            "Describe what you want in `/prompt` - plain words work, @-mentions work best.\n\n"
            f"**Actions I can do:**\n{catalog}\n\n**Tips:**\n"
            "• No channel named? I use the channel you're in.\n"
            "• Unsure? I'll ask a follow-up instead of guessing.\n"
            "• Dangerous actions ask for confirmation first.",
        ),
        ephemeral=True,
    )


async def main():
    # Side-effect imports: each category module registers its actions.
    import src.actions.automod
    import src.actions.channels
    import src.actions.emojis
    import src.actions.events
    import src.actions.guild
    import src.actions.invites
    import src.actions.members
    import src.actions.messages
    import src.actions.roles
    import src.actions.schedules
    import src.actions.system
    import src.actions.threads
    import src.actions.webhooks  # noqa: F401

    check_artifacts_stale()
    print_startup_banner()
    log_startup_checklist(logger=logger)

    from src.ai.needle_agent import prewarm_engine
    from src.scheduler.scheduler import get_scheduler, set_bot

    get_scheduler().start()
    set_bot(bot)
    asyncio.create_task(prewarm_engine())

    token = os.getenv("DISCORD_TOKEN", "mock_discord_token")
    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
    server = uvicorn.Server(config)
    if token == "mock_discord_token":
        log_api_only_mode()
        logger.warning("No valid DISCORD_TOKEN provided. Running in API-only / test mode.")
        await server.serve()
    else:
        logger.info("Starting Discord gateway + FastAPI server...")
        asyncio.create_task(bot.start(token))
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
