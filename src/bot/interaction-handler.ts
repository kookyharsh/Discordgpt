import { Interaction, ChatInputCommandInteraction, ButtonInteraction, MessageFlags } from 'discord.js';
import { GuildRepository, ConfirmationRepository, ExecutionRepository, AuditRepository } from '../database/repositories.js';
import { ActionDispatcher } from '../actions/dispatcher.js';
import { DiscordUIComponents } from './ui.js';
import { createLLMProvider } from '../ai/factory.js';
import { FallbackParser } from '../ai/fallback-parser.js';
import { IntentStatus } from '../ai/types.js';
import { InjectionDefense } from '../security/injection-defense.js';
import { EntityResolver } from '../entities/entity-resolver.js';
import { logger } from '../utils/logger.js';

export class InteractionHandler {
  private llmProvider = createLLMProvider();

  async handleInteraction(interaction: Interaction) {
    try {
      if (interaction.isChatInputCommand()) {
        await this.handleChatInputCommand(interaction);
      } else if (interaction.isButton()) {
        await this.handleButtonInteraction(interaction);
      }
    } catch (err: any) {
      // 10062 = interaction token expired (>3s without ack, or user deleted message).
      // Retrying a reply only produces a second 10062, so just log and stop.
      if (err?.code === 10062 || err?.rawError?.code === 10062) {
        logger.warn('Interaction expired before bot could respond (Unknown interaction). Likely slow ack.');
        return;
      }
      logger.error({ err }, 'Error handling interaction');
      try {
        if (interaction.isRepliable()) {
          const errorUI = DiscordUIComponents.createErrorEmbed('System Error', err.message || 'An unexpected error occurred.');
          if (interaction.deferred || interaction.replied) {
            await interaction.followUp({ ...errorUI, flags: MessageFlags.Ephemeral });
          } else {
            await interaction.reply({ ...errorUI, flags: MessageFlags.Ephemeral });
          }
        }
      } catch (replyErr: any) {
        if (replyErr?.code === 10062) {
          logger.warn('Could not send error message: interaction already expired.');
        } else {
          logger.error({ err: replyErr }, 'Failed to send error response');
        }
      }
    }
  }

  private async handleChatInputCommand(interaction: ChatInputCommandInteraction) {
    if (!interaction.guild || !interaction.member) {
      await interaction.reply({ content: 'Commands can only be used within a server.', flags: MessageFlags.Ephemeral });
      return;
    }

    // ACK FIRST: Discord invalidates the interaction token after 3s.
    // All slow work (member fetch, DB, LLM) must happen after defer.
    const needsEphemeral = interaction.commandName === 'prompt-audit' || interaction.commandName === 'prompt-help';
    try {
      await interaction.deferReply(needsEphemeral ? { flags: MessageFlags.Ephemeral } : undefined);
    } catch (err: any) {
      if (err?.code === 10062) {
        logger.warn('Interaction already expired before defer. Aborting.');
        return;
      }
      throw err;
    }

    const guildId = interaction.guildId!;
    const userId = interaction.user.id;
    const guild = interaction.guild;
    const startedAt = Date.now();
    const ctxBase = { command: interaction.commandName, guildId, userId };
    const stage = (name: string) =>
      logger.info({ ...ctxBase, elapsedMs: Date.now() - startedAt }, `prompt stage: ${name}`);
    stage('deferred - fetching member');

    const member = await guild.members.fetch(userId);
    stage('member fetched - loading guild settings');

    const guildDb = await GuildRepository.findOrCreate(guildId, guild.name);
    const settings = guildDb.settings;
    stage('guild ready');

    if (interaction.commandName === 'prompt') {
      const rawPrompt = interaction.options.getString('request', true);
      const prompt = InjectionDefense.sanitizeExternalText(rawPrompt);
      stage(`prompt received (${prompt.length} chars) - injection check`);

      if (InjectionDefense.detectPromptInjection(prompt)) {
        const errUI = DiscordUIComponents.createErrorEmbed(
          'Security Violation',
          'Prompt contains suspicious system/injection instructions. Request rejected.'
        );
        await interaction.editReply(errUI);
        return;
      }

      let parsed = FallbackParser.parse(prompt);

      if (!parsed) {
        stage('fallback miss - fetching channels/roles for LLM context');
        const channels = (await guild.channels.fetch()).map((c) => ({ id: c?.id || '', name: c?.name || '' }));
        const roles = (await guild.roles.fetch()).map((r) => ({ id: r.id, name: r.name }));

        stage(`context ready (${channels.length} channels, ${roles.length} roles) - calling LLM`);
        // Keep Discord updated so it doesn't look stuck on "thinking".
        await interaction.editReply('Parsing your request with AI - this can take a few seconds…');
        parsed = await this.llmProvider.parseIntent(prompt, {
          guildId,
          channels,
          roles,
          allowedActions: settings?.allowedActions?.length ? settings.allowedActions : ['create_channel', 'delete_channel', 'create_role', 'assign_role', 'timeout_member', 'ban_member', 'send_message'],
        });
        stage(`LLM done - status=${parsed.status}`);
        logger.debug({ ...ctxBase, parsed: JSON.stringify(parsed).slice(0, 1000) }, 'parsed intent');
      } else {
        stage(`fallback hit - action=${parsed.action}`);
      }

      if (parsed.status === IntentStatus.UNSUPPORTED || parsed.status === IntentStatus.REJECTED) {
        stage(`rejected - replying (${parsed.reason?.slice(0, 80) ?? 'no reason'})`);
        const errUI = DiscordUIComponents.createErrorEmbed('Operation Rejected', parsed.reason || 'This request is unsupported or violates safety guidelines.');
        await interaction.editReply(errUI);
        return;
      }

      if (parsed.status === IntentStatus.CLARIFICATION_REQUIRED) {
        stage('clarification required - replying');
        const errUI = DiscordUIComponents.createErrorEmbed('Clarification Required', parsed.question || 'Please provide more details.');
        await interaction.editReply(errUI);
        return;
      }

      if (parsed.status === IntentStatus.DIRECT_ACTION && parsed.action) {
        stage(`dispatching action=${parsed.action}`);
        const execution = await ExecutionRepository.createExecution({
          guildId,
          userId,
          prompt,
          status: 'RUNNING',
          parsedIntent: parsed,
        });

        const ctx = {
          guildId,
          userId,
          executionId: execution.id,
          guild,
          actorMember: member,
          settings,
        };

        let actionType = parsed.action;
        let params = parsed.parameters || {};

        if (params.channelName) {
          const res = await EntityResolver.resolveChannel(guild, params.channelName);
          if (res.resolved) params.channelId = res.resolved.id;
        }

        const dispatchRes = await ActionDispatcher.dispatch(actionType, params, ctx);
        stage(
          dispatchRes.requiresConfirmation
            ? 'dispatch needs confirmation - replying'
            : dispatchRes.success
              ? `dispatch ok - replying`
              : `dispatch failed (${dispatchRes.error?.slice(0, 80) ?? 'unknown'}) - replying`
        );

        if (dispatchRes.requiresConfirmation && dispatchRes.confirmationDetails) {
          const ui = DiscordUIComponents.createConfirmationEmbed(
            dispatchRes.confirmationDetails.actionType,
            dispatchRes.confirmationDetails.riskLevel,
            JSON.stringify(params, null, 2),
            dispatchRes.confirmationDetails.actionNonce
          );
          await interaction.editReply(ui);
          return;
        }

        if (dispatchRes.success) {
          const ui = DiscordUIComponents.createSuccessEmbed('Action Executed', `Successfully performed **${actionType}**.`);
          await interaction.editReply(ui);
        } else {
          const ui = DiscordUIComponents.createErrorEmbed('Action Failed', dispatchRes.error || 'Execution failed.');
          await interaction.editReply(ui);
        }
      } else {
        // Catch-all: UNSUPPORTED/REJECTED/CLARIFICATION/DIRECT_ACTION are handled
        // above, but the model can also return action_plan, confirmation_required,
        // capability_unavailable, permission_analysis_required, or a direct_action
        // with no action. Without this the bot sits on "thinking" forever.
        stage(`unhandled intent (status=${parsed.status}, action=${parsed.action ?? 'none'}) - replying`);
        const detail =
          parsed.status === IntentStatus.DIRECT_ACTION
            ? 'The AI response did not include an executable action. Try rephrasing with a concrete operation.'
            : `The AI returned status "${parsed.status}", which this bot cannot execute yet. Try a single concrete operation (e.g. "Create channel welcome").`;
        await interaction.editReply(
          DiscordUIComponents.createErrorEmbed('Operation Rejected', parsed.reason || detail)
        );
      }
    } else if (interaction.commandName === 'prompt-audit') {
      const logs = await AuditRepository.getRecentLogs(guildId, 10);
      const logSummary = logs.map((l: { createdAt: Date; action: string; userId: string; status: string }) => `• [${l.createdAt.toISOString()}] **${l.action}** by <@${l.userId}>: ${l.status}`).join('\n') || 'No audit logs found.';
      await interaction.editReply({ embeds: [DiscordUIComponents.createSuccessEmbed('Recent Audit Logs', logSummary).embeds[0]] });
    } else if (interaction.commandName === 'prompt-help') {
      await interaction.editReply({
        embeds: [
          DiscordUIComponents.createSuccessEmbed(
            'Natural Language Bot Help',
            'You can describe operations using `/prompt`!\n\n**Supported Actions:**\n• Create Channel: `Create channel welcome`\n• Delete Channel: `Delete #old-chat`\n• Create Role: `Create role Moderators`\n• Assign Role: `Give @Alex role Support`\n• Timeout Member: `Timeout @BadActor for 300 seconds`\n• Ban Member: `Ban @Spammer`'
          ).embeds[0]
        ],
      });
    }
  }

  private async handleButtonInteraction(interaction: ButtonInteraction) {
    const customId = interaction.customId;
    if (customId.startsWith('confirm:') || customId.startsWith('cancel:')) {
      const [action, nonce] = customId.split(':');
      const guildId = interaction.guildId!;
      const userId = interaction.user.id;

      if (action === 'cancel') {
        await interaction.update(DiscordUIComponents.createErrorEmbed('Action Cancelled', 'The confirmation was explicitly cancelled by user.'));
        return;
      }

      // ACK before slow DB + Discord work (3s interaction window).
      // After deferUpdate, respond with editReply (update would throw).
      try {
        await interaction.deferUpdate();
      } catch (err: any) {
        if (err?.code === 10062) {
          logger.warn('Button interaction already expired before ack. Aborting.');
          return;
        }
        throw err;
      }

      const confirmation = await ConfirmationRepository.findAndConsume(nonce, guildId, userId, '');
      if (!confirmation) {
        await interaction.editReply(DiscordUIComponents.createErrorEmbed('Invalid or Expired Confirmation', 'This confirmation has expired, was already consumed, or belonged to another user.'));
        return;
      }

      const plan = confirmation.actionPlan as any;
      const guild = interaction.guild!;
      const member = await guild.members.fetch(userId);

      const ctx = {
        guildId,
        userId,
        executionId: `conf-${Date.now()}`,
        guild,
        actorMember: member,
      };

      const actionDef = (await import('../actions/registry.js')).ActionRegistry.get(plan.type);
      if (!actionDef) {
        await interaction.editReply(DiscordUIComponents.createErrorEmbed('Execution Failed', 'Action definition no longer exists.'));
        return;
      }

      try {
        await actionDef.handler(ctx, plan.input);
        await interaction.editReply(DiscordUIComponents.createSuccessEmbed('Action Executed', `Successfully executed confirmed operation **${plan.type}**.`));
      } catch (err: any) {
        await interaction.editReply(DiscordUIComponents.createErrorEmbed('Execution Failed', err.message));
      }
    }
  }
}
