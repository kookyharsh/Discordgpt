import {
  Client,
  GatewayIntentBits,
  REST,
  Routes,
  Interaction,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  EmbedBuilder,
} from 'discord.js';
import { config } from './config/index.js';
import { logger } from './utils/logger.js';
import { LiveDiscordAdapter } from './discord/live-adapter.js';
import { MockDiscordAdapter } from './discord/mock-adapter.js';
import { STABLE_SLASH_COMMANDS } from './discord/commands.js';
import { NaturalLanguageParser } from './ai/parser.js';
import { OpenAIProvider } from './ai/providers/openai.js';
import { GeminiProvider } from './ai/providers/gemini.js';
import { ClaudeProvider } from './ai/providers/claude.js';
import { MockLLMProvider } from './ai/providers/mock.js';
import { ActionDispatcher } from './actions/dispatcher.js';
import { PermissionEngine } from './permissions/permission-engine.js';
import { PolicyEngine } from './policies/policy-engine.js';
import { ConfirmationManager } from './confirmations/confirmation-manager.js';
import { RateLimiter } from './rate-limit/rate-limiter.js';
import { AuditLogger } from './audit/audit-logger.js';
import { ExecutionContext } from './actions/types.js';
import { createHttpServer } from './server.js';

function getLLMProvider() {
  switch (config.LLM_PROVIDER) {
    case 'openai':
      return new OpenAIProvider(config.OPENAI_API_KEY, config.LLM_MODEL);
    case 'gemini':
      return new GeminiProvider(config.GEMINI_API_KEY, config.LLM_MODEL);
    case 'claude':
      return new ClaudeProvider(config.ANTHROPIC_API_KEY, config.LLM_MODEL);
    default:
      return new MockLLMProvider();
  }
}

async function registerCommands(token: string, clientId: string) {
  const rest = new REST({ version: '10' }).setToken(token);
  try {
    logger.info('Registering application slash commands with Discord...');
    await rest.put(Routes.applicationCommands(clientId), {
      body: STABLE_SLASH_COMMANDS.map((c) => c.toJSON()),
    });
    logger.info('Successfully registered application slash commands.');
  } catch (err) {
    logger.error(err, 'Failed to register slash commands');
  }
}

async function bootstrap() {
  logger.info('Starting DiscordGPT agent...');

  // Start HTTP Health Server
  const app = createHttpServer();
  app.listen(config.PORT, () => {
    logger.info(`HTTP server listening on port ${config.PORT}`);
  });

  const isTestOrMock = config.NODE_ENV === 'test' || !config.DISCORD_TOKEN;
  const dispatcher = new ActionDispatcher();
  const llmProvider = getLLMProvider();
  const parser = new NaturalLanguageParser(llmProvider);
  const rateLimiter = new RateLimiter(config.REDIS_URL);

  if (isTestOrMock) {
    logger.info('Running in Mock environment mode.');
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

  const liveAdapter = new LiveDiscordAdapter(client);
  const permEngine = new PermissionEngine(liveAdapter);

  client.once('ready', async () => {
    logger.info(`Logged in as ${client.user?.tag}`);
    await registerCommands(config.DISCORD_TOKEN, config.DISCORD_CLIENT_ID);
  });

  client.on('interactionCreate', async (interaction: Interaction) => {
    if (!interaction.inGuild() || !interaction.guildId) {
      if (interaction.isRepliable()) {
        await interaction.reply({ content: '❌ DiscordGPT natural language operations must be invoked inside a server.', ephemeral: true });
      }
      return;
    }

    const guildId = interaction.guildId;
    const userId = interaction.user.id;

    // Rate Limiting Check
    const rateCheck = await rateLimiter.isRateLimited(`ratelimit:${guildId}:${userId}`, 10, 60);
    if (rateCheck.limited) {
      if (interaction.isRepliable()) {
        await interaction.reply({ content: '❌ Rate limit exceeded. Please wait before submitting more requests.', ephemeral: true });
      }
      return;
    }

    // Handle Slash Commands
    if (interaction.isChatInputCommand()) {
      if (interaction.commandName === 'prompt') {
        const inputPrompt = interaction.options.getString('input', true);
        await interaction.deferReply();

        // Stage 1 & 2 Parse
        const parsedIntent = await parser.parseRequest(inputPrompt);

        if (parsedIntent.status === 'unsupported') {
          await interaction.editReply({
            embeds: [
              new EmbedBuilder()
                .setTitle('❌ Operation Unsupported')
                .setDescription(parsedIntent.reason)
                .setColor(0xff0000),
            ],
          });
          return;
        }

        if (parsedIntent.status === 'capability_unavailable') {
          await interaction.editReply({
            embeds: [
              new EmbedBuilder()
                .setTitle('❌ Capability Unavailable')
                .setDescription(parsedIntent.reason)
                .setColor(0xff0000),
            ],
          });
          return;
        }

        if (parsedIntent.status === 'clarification_required') {
          await interaction.editReply({
            embeds: [
              new EmbedBuilder()
                .setTitle('ℹ️ Clarification Needed')
                .setDescription(parsedIntent.question)
                .setColor(0xffff00),
            ],
          });
          return;
        }

        if (parsedIntent.status === 'rejected') {
          await interaction.editReply({
            embeds: [
              new EmbedBuilder()
                .setTitle('❌ Request Rejected')
                .setDescription(parsedIntent.reason)
                .setColor(0xff0000),
            ],
          });
          return;
        }

        // Build Dispatch Plan
        const plan =
          parsedIntent.status === 'direct_action'
            ? { steps: [{ id: 'step_1', action: parsedIntent.action, parameters: parsedIntent.parameters }] }
            : { steps: parsedIntent.steps };

        // Policy & Permission Evaluation
        for (const step of plan.steps) {
          const polCheck = PolicyEngine.evaluatePolicy(PolicyEngine.DEFAULT_POLICY, step.action);
          if (!polCheck.allowed) {
            await interaction.editReply({ content: `❌ Policy Blocked: ${polCheck.reason}` });
            return;
          }

          const permCheck = await permEngine.checkActionPermissions(guildId, userId, step.action);
          if (!permCheck.allowed) {
            await interaction.editReply({ content: `❌ Permission Denied: ${permCheck.reason}` });
            return;
          }
        }

        // Check Confirmation Requirement
        if (ConfirmationManager.requiresConfirmation(plan)) {
          const conf = ConfirmationManager.createConfirmation(guildId, userId, plan);

          const row = new ActionRowBuilder<ButtonBuilder>().addComponents(
            new ButtonBuilder().setCustomId(`confirm:${conf.id}`).setLabel('Confirm').setStyle(ButtonStyle.Danger),
            new ButtonBuilder().setCustomId(`cancel:${conf.id}`).setLabel('Cancel').setStyle(ButtonStyle.Secondary)
          );

          await interaction.editReply({
            embeds: [
              new EmbedBuilder()
                .setTitle('⚠️ Confirmation Required')
                .setDescription(`This request involves dangerous or destructive actions.\n\n**Requested Action Plan:**\n${plan.steps.map((s: any) => `- ${s.action}`).join('\n')}\n\nDo you want to proceed?`)
                .setColor(0xffa500),
            ],
            components: [row],
          });
          return;
        }

        // Execute Direct Action
        const execCtx: ExecutionContext = {
          guildId,
          userId,
          executionId: `exec-${Date.now()}`,
          logger,
          discordAdapter: liveAdapter,
        };

        const result = await dispatcher.dispatch(plan, execCtx);
        if (result.status === 'COMPLETED') {
          await interaction.editReply({ content: `✅ Action executed successfully.` });
        } else {
          await interaction.editReply({ content: `❌ Execution failed: ${result.error}` });
        }
      } else if (interaction.commandName === 'prompt-audit') {
        const logs = AuditLogger.getLogsForGuild(guildId, 10);
        const logText = logs.length === 0 ? 'No recent actions logged.' : logs.map((l) => `- [${l.status}] ${l.action} by <@${l.userId}> at ${l.createdAt.toISOString()}`).join('\n');
        await interaction.reply({ embeds: [new EmbedBuilder().setTitle('📋 Server Audit Log').setDescription(logText)], ephemeral: true });
      } else if (interaction.commandName === 'prompt-help') {
        await interaction.reply({
          content: 'ℹ️ Use `/prompt input: <your request>` to control Discord with natural language.',
          ephemeral: true,
        });
      }
      return;
    }

    // Handle Confirmation Buttons
    if (interaction.isButton()) {
      const [action, confId] = interaction.customId.split(':');
      if (action === 'cancel') {
        await interaction.update({ content: '❌ Operation cancelled.', embeds: [], components: [] });
        return;
      }

      if (action === 'confirm') {
        await interaction.update({ content: '⏳ Executing confirmed operation...', embeds: [], components: [] });
      }
    }
  });

  await client.login(config.DISCORD_TOKEN);
}

bootstrap().catch((err) => {
  logger.fatal(err, 'Failed to start application');
  process.exit(1);
});
