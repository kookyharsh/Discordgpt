import { Client, GatewayIntentBits } from 'discord.js';
import { config } from './config/index.js';
import { logger } from './utils/logger.js';
import { LiveDiscordAdapter } from './discord/live-adapter.js';
import { MockDiscordAdapter } from './discord/mock-adapter.js';
import { createHttpServer } from './server.js';

async function bootstrap() {
  logger.info('Starting DiscordGPT agent...');

  // Start HTTP Health Server
  const server = createHttpServer();
  server.listen(config.PORT, () => {
    logger.info(`HTTP server listening on port ${config.PORT}`);
  });

  if (config.NODE_ENV === 'test' || config.DISCORD_TOKEN === 'mock_token') {
    logger.info('Running with MockDiscordAdapter');
    return;
  }

  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.GuildMembers,
      GatewayIntentBits.MessageContent,
    ],
  });

  client.once('ready', () => {
    logger.info(`Logged in as ${client.user?.tag}`);
  });

  await client.login(config.DISCORD_TOKEN);
}

bootstrap().catch((err) => {
  logger.fatal(err, 'Failed to start application');
  process.exit(1);
});
