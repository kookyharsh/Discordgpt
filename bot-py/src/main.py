import asyncio
import logging
import os

import discord
import uvicorn
from discord.ext import commands

from src.api.server import app as fastapi_app
from src.bot.interaction_handler import BotInteractionHandler

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("discord_agent_main")

intents = discord.Intents.none()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
handler = BotInteractionHandler(bot)


@bot.event
async def on_ready():
    logger.info("Bot connected as %s (ID: %s)", bot.user, getattr(bot.user, "id", "?"))
    try:
        synced = await bot.tree.sync()
        logger.info("Synced %d slash commands.", len(synced))
    except Exception as e:
        logger.error("Failed to sync commands: %s", e)


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
        db_guild = await GuildRepository.find_or_create(
            session, str(interaction.guild.id), interaction.guild.name
        )
        logs = await AuditRepository.get_recent_logs(session, db_guild.id, 10)
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
    # Side-effect import: registers all @needle.tool actions into ActionRegistry.
    import src.actions.advanced_tools
    import src.actions.extra_tools
    import src.actions.needle_tools  # noqa: F401

    token = os.getenv("DISCORD_TOKEN", "mock_discord_token")
    config = uvicorn.Config(
        fastapi_app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info"
    )
    server = uvicorn.Server(config)
    if token == "mock_discord_token":
        logger.warning("No valid DISCORD_TOKEN provided. Running in API-only / test mode.")
        await server.serve()
    else:
        asyncio.create_task(bot.start(token))
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
