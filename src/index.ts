import { Client, Events, GatewayIntentBits, REST, Routes } from 'discord.js';
import { config } from './config/index.js';
import { createFastifyServer } from './bot/server.js';
import { applicationCommands } from './bot/commands.js';
import { InteractionHandler } from './bot/interaction-handler.js';
import { logger } from './utils/logger.js';
import { prisma } from './database/prisma.js';

// Register all whitelisted actions (side-effect imports populate ActionRegistry).
import './actions/channel-actions.js';
import './actions/role-actions.js';
import './actions/member-actions.js';
import './actions/message-actions.js';

const server = createFastifyServer();
const interactionHandler = new InteractionHandler();

async function registerCommands() {
	logger.info('Registering Discord slash commands...');
	const rest = new REST({ version: '10' }).setToken(config.DISCORD_TOKEN);
	const body = applicationCommands.map((c) => c.toJSON());
	await rest.put(Routes.applicationCommands(config.DISCORD_CLIENT_ID), { body });
	logger.info({ count: body.length }, 'Slash commands registered');
}

async function checkDatabase() {
	try {
		await prisma.$queryRaw`SELECT 1`;
		logger.info('Database connected');
	} catch (err: any) {
		logger.warn({ err: err?.message }, 'Database not reachable - bot will continue but DB-backed features will fail. Run Postgres + `prisma migrate dev`');
	}
}

function createDiscordClient(): Client {
	const client = new Client({
		// Guilds only: GuildMembers is a privileged intent that throws
		// "Used disallowed intents" unless enabled in the Developer Portal.
		// All member lookups in this bot use REST fetch (guild.members.fetch),
		// which works without the privileged gateway intent.
		intents: [GatewayIntentBits.Guilds],
	});

	client.once(Events.ClientReady, (readyClient) => {
		logger.info({ user: readyClient.user.tag }, 'Discord client ready');
	});

	client.on(Events.InteractionCreate, async (interaction) => {
		await interactionHandler.handleInteraction(interaction);
	});

	client.on(Events.Error, (err) => {
		logger.error({ err }, 'Discord client error');
	});

	return client;
}

const start = async () => {
	try {
		logger.info({ env: config.NODE_ENV, port: config.PORT }, 'Starting Discord Natural Language Agent Service...');

		if (!config.DISCORD_TOKEN || config.DISCORD_TOKEN === 'mock_discord_token') {
			logger.error('DISCORD_TOKEN is missing or still the mock default. Set a real bot token in .env - aborting Discord login.');
			process.exitCode = 1;
			// Still start HTTP so /health explains the misconfiguration.
		}

		if (!config.DISCORD_CLIENT_ID || config.DISCORD_CLIENT_ID === 'mock_discord_client_id') {
			logger.warn('DISCORD_CLIENT_ID is missing or still the mock default. Slash command registration will fail - set it in .env');
		}

		// 1. HTTP server (health/ready/metrics). Await so port conflicts fail fast.
		await server.listen({ host: '0.0.0.0', port: config.PORT });
		logger.info({ port: config.PORT }, 'HTTP server listening');

		// 2. Database connectivity check (non-fatal, logs clearly).
		await checkDatabase();

		// 3. Discord login (this is what was missing - previously the process just idled here).
		if (process.exitCode && process.exitCode !== 0) return;

		const client = createDiscordClient();

		logger.info('Logging in to Discord...');
		await client.login(config.DISCORD_TOKEN);
		// ClientReady event fires async after login; log immediately so users see progress.
		logger.info('Discord login request sent, waiting for ready event...');

		try {
			await registerCommands();
		} catch (err: any) {
			logger.error({ err: err?.message ?? err }, 'Slash command registration failed. Check DISCORD_CLIENT_ID and bot token.');
		}

		// Optional scheduler: requires Redis. Start lazily so a missing Redis doesn't hang boot.
		try {
			const { ActionScheduler } = await import('./scheduler/scheduler.js');
			const scheduler = new ActionScheduler();
			await scheduler.startWorker(client);
			await scheduler.reconcileSchedules(client);
			logger.info('Action scheduler started');
		} catch (err: any) {
			logger.warn({ err: err?.message ?? err }, 'Scheduler not started (is Redis running at REDIS_URL?). Scheduled jobs disabled.');
		}

		const shutdown = async (signal: string) => {
			logger.info({ signal }, 'Shutting down...');
			try {
				client.destroy();
				await prisma.$disconnect();
				await server.close();
			} finally {
				process.exit(0);
			}
		};
		process.on('SIGINT', () => void shutdown('SIGINT'));
		process.on('SIGTERM', () => void shutdown('SIGTERM'));
	} catch (err) {
		logger.error({ err }, 'Unable to start service');
		process.exitCode = 1;
	}
};

void start();
