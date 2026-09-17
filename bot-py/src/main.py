import asyncio
import logging
import os

import discord
import uvicorn
from discord.ext import commands

from src.api.server import app as fastapi_app
from src.bot.interaction_handler import BotInteractionHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord_agent_main")

intents = discord.Intents.none()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
handler = BotInteractionHandler(bot)

@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.tree.command(name="prompt", description="Execute natural language Discord management operations")
async def prompt_slash(interaction: discord.Interaction, request: str):
    await handler.handle_prompt(interaction, request)

async def main():
    token = os.getenv("DISCORD_TOKEN", "mock_discord_token")
    if token == "mock_discord_token":
        logger.warning("No valid DISCORD_TOKEN provided. Running in API-only / test mode.")
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        asyncio.create_task(bot.start(token))
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
