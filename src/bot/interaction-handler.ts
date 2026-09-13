import { Interaction, ChatInputCommandInteraction, ButtonInteraction, ModalSubmitInteraction, MessageFlags, Guild, GuildMember } from 'discord.js';
import { GuildRepository, ConfirmationRepository, ExecutionRepository, AuditRepository, ScheduledActionRepository, ConversationRepository, PendingQuestionRepository } from '../database/repositories.js';
import { ActionDispatcher } from '../actions/dispatcher.js';
import { DiscordUIComponents } from './ui.js';
import { parseSettingValue, settingField } from './setting-options.js';
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
      } else if (interaction.isModalSubmit()) {
        await this.handleModalSubmit(interaction);
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
    // All info commands reply ephemeral; /prompt stays public.
    const needsEphemeral =
      interaction.commandName === 'prompt-audit' ||
      interaction.commandName === 'prompt-help' ||
      interaction.commandName === 'prompt-schedules' ||
      interaction.commandName === 'prompt-settings';
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
      await this.runPromptFlow(interaction, {
        guild,
        actorMember: member,
        guildId,
        userId,
        settings,
        stage,
        ctxBase,
      }, rawPrompt);
    } else if (interaction.commandName === 'prompt-audit') {
      stage('listing audit logs');
      const logs = await AuditRepository.getRecentLogs(guildId, 10);
      const logSummary = logs.map((l: { createdAt: Date; action: string; userId: string; status: string }) => `• [${l.createdAt.toISOString()}] **${l.action}** by <@${l.userId}>: ${l.status}`).join('\n') || 'No audit logs found.';
      await interaction.editReply({ embeds: [DiscordUIComponents.createSuccessEmbed('Recent Audit Logs', logSummary).embeds[0]] });
    } else if (interaction.commandName === 'prompt-schedules') {
      const cancelId = interaction.options.getString('cancel_id', false)?.trim();
      if (cancelId) {
        stage(`cancelling schedule ${cancelId}`);
        const result = await ScheduledActionRepository.delete(cancelId, guildId);
        if (result.count === 0) {
          await interaction.editReply(
            DiscordUIComponents.createErrorEmbed('Schedule Not Found', `No active schedule with ID \`${cancelId}\` in this server.`)
          );
        } else {
          stage('schedule cancelled');
          await interaction.editReply({
            embeds: [DiscordUIComponents.createSuccessEmbed('Schedule Cancelled', `Cancelled schedule \`${cancelId}\`. Already-queued runs are skipped automatically.`).embeds[0]],
          });
        }
        return;
      }
      stage('listing schedules');
      const schedules = await ScheduledActionRepository.listActiveForGuild(guildId);
      const lines = schedules.map((s) => {
        const plan = s.actionPlan as any;
        const when = s.cronExpression
          ? `cron \`${s.cronExpression}\`${s.timezone ? ` (${s.timezone})` : ''}`
          : s.executeAt
            ? `once at ${s.executeAt.toISOString()}`
            : 'manual';
        const next = s.nextRunAt ? `, next ${s.nextRunAt.toISOString()}` : '';
        return `• \`${s.id}\` **${plan?.type ?? 'unknown'}** — ${when}${next}`;
      });
      await interaction.editReply({
        embeds: [
          DiscordUIComponents.createSuccessEmbed(
            'Active Schedules',
            lines.length > 0
              ? `${lines.join('\n')}\n\nCancel one with \`/prompt-schedules cancel_id:<id>\`.`
              : 'No active schedules in this server.'
          ).embeds[0],
        ],
      });
    } else if (interaction.commandName === 'prompt-settings') {
      const key = interaction.options.getString('key', false);
      const value = interaction.options.getString('value', false);
      if (!key) {
        stage('showing settings');
        const s = settings;
        const summary =
          `**Enabled:** ${s?.enabled ?? true}\n` +
          `**Timezone:** ${s?.timezone ?? 'UTC'}\n` +
          `**Allowed actions:** ${(s?.allowedActions?.length ? s.allowedActions : ['(all)']).join(', ')}\n` +
          `**Disabled actions:** ${(s?.disabledActions?.length ? s.disabledActions.join(', ') : '(none)')}\n\n` +
          `Change one with \`/prompt-settings key:<key> value:<value>\`.`;
        await interaction.editReply({
          embeds: [DiscordUIComponents.createSuccessEmbed('Server Settings', summary).embeds[0]],
        });
        return;
      }
      if (!value) {
        await interaction.editReply(
          DiscordUIComponents.createErrorEmbed('Missing Value', `Provide a value: \`/prompt-settings key:${key} value:…\`.`)
        );
        return;
      }
      stage(`updating setting ${key}`);
      const parsed = parseSettingValue(key, value);
      const field = settingField(key);
      if (!parsed.ok || !field) {
        await interaction.editReply(
          DiscordUIComponents.createErrorEmbed('Invalid Setting', parsed.error ?? `Unknown setting "${key}".`)
        );
        return;
      }
      await GuildRepository.updateSettings(guildId, { [field]: parsed.value });
      stage('setting updated');
      const display = Array.isArray(parsed.value) ? (parsed.value.length ? parsed.value.join(', ') : '(cleared)') : String(parsed.value);
      await interaction.editReply({
        embeds: [DiscordUIComponents.createSuccessEmbed('Setting Updated', `**${field}** is now \`${display}\`.`).embeds[0]],
      });
    } else if (interaction.commandName === 'prompt-help') {
      stage('showing help');
      await interaction.editReply({
        embeds: [
          DiscordUIComponents.createSuccessEmbed(
            'Natural Language Bot Help',
            'You can describe operations using `/prompt`!\n\n**Supported Actions:**\n• Create Channel: `Create channel welcome`\n• Delete Channel: `Delete #old-chat`\n• Create Role: `Create role Moderators`\n• Assign Role: `Give @Alex role Support`\n• Timeout Member: `Timeout @BadActor for 300 seconds`\n• Ban Member: `Ban @Spammer`'
          ).embeds[0]
        ],
      });
    } else {
      // Future-proof: every registered command must produce a reply.
      stage(`unknown command ${interaction.commandName} - replying`);
      await interaction.editReply(
        DiscordUIComponents.createErrorEmbed('Unknown Command', `The command "${interaction.commandName}" is not implemented yet.`)
      );
    }
  }

  private async loadHistory(guildId: string, userId: string, channelId: string) {
    try {
      const convo = await ConversationRepository.getOrCreate(guildId, userId, channelId);
      return { id: convo.id as string | null, lines: await ConversationRepository.historyLines(convo.id) };
    } catch (err: any) {
      logger.warn({ err: err?.message ?? err }, 'Conversation history unavailable - continuing without memory');
      return { id: null as string | null, lines: [] as string[] };
    }
  }

  private async remember(convoId: string | null, userText: string, assistantText: string) {
    if (!convoId) return;
    try {
      await ConversationRepository.append(convoId, 'user', userText);
      await ConversationRepository.append(convoId, 'assistant', assistantText);
    } catch (err: any) {
      logger.warn({ err: err?.message ?? err }, 'Conversation memory write failed');
    }
  }

  /**
   * Shared /prompt pipeline for slash commands and clarification-followup modals.
   * The interaction must already be deferred; all replies go through editReply.
   */
  private async runPromptFlow(
    interaction: ChatInputCommandInteraction | ModalSubmitInteraction,
    env: {
      guild: Guild;
      actorMember: GuildMember;
      guildId: string;
      userId: string;
      settings: any;
      stage: (name: string) => void;
      ctxBase: { command: string; guildId: string; userId: string };
    },
    rawPrompt: string
  ) {
    const { guild, actorMember, guildId, userId, settings, stage, ctxBase } = env;
    const channelId = interaction.channelId ?? guildId;
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

    const { id: convoId, lines: history } = await this.loadHistory(guildId, userId, channelId);

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
        history,
      });
      stage(`LLM done - status=${parsed.status}`);
      logger.debug({ ...ctxBase, parsed: JSON.stringify(parsed).slice(0, 1000) }, 'parsed intent');
    } else {
      stage(`fallback hit - action=${parsed.action}`);
    }

    if (parsed.status === IntentStatus.UNSUPPORTED || parsed.status === IntentStatus.REJECTED) {
      stage(`rejected - replying (${parsed.reason?.slice(0, 80) ?? 'no reason'})`);
      const reason = parsed.reason || 'This request is unsupported or violates safety guidelines.';
      await interaction.editReply(DiscordUIComponents.createErrorEmbed('Operation Rejected', reason));
      await this.remember(convoId, prompt, `I couldn't do that: ${reason.slice(0, 300)}`);
      return;
    }

    if (parsed.status === IntentStatus.CHAT) {
      stage('chat - replying');
      const text = parsed.message?.trim().slice(0, 1900) || await this.chatReply(prompt, { guildId, guild, userId, history });
      await interaction.editReply(text);
      await this.remember(convoId, prompt, text.slice(0, 500));
      return;
    }

    if (parsed.status === IntentStatus.CLARIFICATION_REQUIRED) {
      const question = parsed.question || 'Please provide more details.';
      stage(`clarification - storing pending question`);
      try {
        const pending = await PendingQuestionRepository.create({
          guildId,
          userId,
          channelId,
          question,
          originalPrompt: prompt,
        });
        await interaction.editReply(DiscordUIComponents.createQuestionEmbed(question, pending.id));
        await this.remember(convoId, prompt, `I asked: ${question.slice(0, 300)}`);
      } catch (err: any) {
        logger.error({ err: err?.message ?? err }, 'Failed to store pending question');
        await interaction.editReply(
          DiscordUIComponents.createErrorEmbed('Clarification Required', `${question}\n\n(Please run /prompt again with the answer.)`)
        );
      }
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
        actorMember,
        settings,
      };

      const actionType = parsed.action;
      const params = parsed.parameters || {};

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
        await this.remember(convoId, prompt, `I asked for confirmation before doing ${actionType}.`);
        return;
      }

      if (dispatchRes.success) {
        const text = `Successfully performed **${actionType}**.`;
        await interaction.editReply(DiscordUIComponents.createSuccessEmbed('Action Executed', text));
        await this.remember(convoId, prompt, `I did ${actionType} successfully.`);
      } else {
        const errText = dispatchRes.error || 'Execution failed.';
        await interaction.editReply(DiscordUIComponents.createErrorEmbed('Action Failed', errText));
        await this.remember(convoId, prompt, `That failed: ${errText.slice(0, 300)}`);
      }
    } else {
      // Catch-all: the model can also return action_plan, confirmation_required,
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
      await this.remember(convoId, prompt, `I couldn't do that: ${(parsed.reason || detail).slice(0, 300)}`);
    }
  }

  /** Free-chat reply with history context; provider mismatch falls back gracefully. */
  private async chatReply(
    prompt: string,
    context: { guildId: string; guild: Guild; userId: string; history: string[] }
  ): Promise<string> {
    try {
      const channels = (await context.guild.channels.fetch()).map((c) => ({ id: c?.id || '', name: c?.name || '' }));
      const roles = (await context.guild.roles.fetch()).map((r) => ({ id: r.id, name: r.name }));
      if (typeof this.llmProvider.chat === 'function') {
        return await this.llmProvider.chat(prompt, {
          guildId: context.guildId,
          channels,
          roles,
          allowedActions: [],
          history: context.history,
        });
      }
    } catch (err: any) {
      logger.error({ err: err?.message ?? err }, 'Chat reply failed');
    }
    return "I'm not sure how to help with that yet. Try asking me to do something concrete like `Create channel welcome`.";
  }

  private async handleModalSubmit(interaction: ModalSubmitInteraction) {
    if (!interaction.customId.startsWith('clarify-modal:')) {
      if (!interaction.replied && !interaction.deferred) {
        await interaction.reply({ content: 'Unknown form.', flags: MessageFlags.Ephemeral }).catch(() => undefined);
      }
      return;
    }
    if (!interaction.guild) {
      await interaction.reply({ content: 'Follow-ups can only be used within a server.', flags: MessageFlags.Ephemeral });
      return;
    }
    try {
      await interaction.deferReply();
    } catch (err: any) {
      if (err?.code === 10062) {
        logger.warn('Modal interaction already expired before defer. Aborting.');
        return;
      }
      throw err;
    }

    const pendingId = interaction.customId.split(':')[1] ?? '';
    const guildId = interaction.guildId!;
    const userId = interaction.user.id;
    const guild = interaction.guild;
    const startedAt = Date.now();
    const ctxBase = { command: 'prompt-followup', guildId, userId };
    const stage = (name: string) =>
      logger.info({ ...ctxBase, elapsedMs: Date.now() - startedAt }, `prompt stage: ${name}`);
    stage('followup deferred - consuming pending question');

    const pending = await PendingQuestionRepository.consume(pendingId, guildId, userId);
    if (!pending) {
      await interaction.editReply(
        DiscordUIComponents.createErrorEmbed(
          'Answer Expired',
          'This question already expired, was answered, or belongs to someone else. Run /prompt again.'
        )
      );
      return;
    }

    const answer = interaction.fields.getTextInputValue('answer');
    stage(`answer received (${answer.length} chars) - resuming`);
    const member = await guild.members.fetch(userId);
    const guildDb = await GuildRepository.findOrCreate(guildId, guild.name);
    await this.runPromptFlow(interaction, {
      guild,
      actorMember: member,
      guildId,
      userId,
      settings: guildDb.settings,
      stage,
      ctxBase,
    }, `${pending.originalPrompt}\nAdditional detail from user: ${answer}`);
  }

  private async handleButtonInteraction(interaction: ButtonInteraction) {
    const customId = interaction.customId;

    if (customId.startsWith('clarify-answer:')) {
      // showModal IS the ack - never defer before it.
      const pendingId = customId.split(':')[1] ?? '';
      await interaction.showModal(DiscordUIComponents.createAnswerModal(pendingId, 'Additional detail'));
      return;
    }

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
