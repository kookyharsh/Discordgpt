import { z } from 'zod';
import { PermissionFlagsBits, TextChannel } from 'discord.js';
import { ActionDefinition, ConfirmationPolicy, RiskLevel } from './types.js';
import { ActionRegistry } from './registry.js';

export const sendMessageAction: ActionDefinition = {
  type: 'send_message',
  description: 'Sends a message to a specific channel.',
  inputSchema: z.object({
    channelId: z.string(),
    content: z.string().min(1).max(2000),
  }),
  requiredBotPermissions: [PermissionFlagsBits.SendMessages],
  requiredUserPermissions: [PermissionFlagsBits.SendMessages],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased()) {
      throw new Error(`Text channel ${input.channelId} not found.`);
    }

    const message = await (channel as TextChannel).send(input.content);

    return {
      messageId: message.id,
      channelId: channel.id,
      sent: true,
    };
  },
};

ActionRegistry.register(sendMessageAction);

export const pinMessageAction: ActionDefinition = {
  type: 'pin_message',
  description: 'Pins a message in a text channel.',
  inputSchema: z.object({
    channelId: z.string(),
    messageId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageMessages],
  requiredUserPermissions: [PermissionFlagsBits.ManageMessages],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased()) {
      throw new Error(`Text channel ${input.channelId} not found.`);
    }

    const message = await channel.messages.fetch(input.messageId);
    if (!message) throw new Error(`Message ${input.messageId} not found.`);
    if (message.pinned) return { messageId: message.id, pinned: true, note: 'Already pinned.' };

    await message.pin(input.reason);

    return {
      messageId: message.id,
      pinned: true,
    };
  },
};

export const unpinMessageAction: ActionDefinition = {
  type: 'unpin_message',
  description: 'Unpins a message in a text channel.',
  inputSchema: z.object({
    channelId: z.string(),
    messageId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageMessages],
  requiredUserPermissions: [PermissionFlagsBits.ManageMessages],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased()) {
      throw new Error(`Text channel ${input.channelId} not found.`);
    }

    const message = await channel.messages.fetch(input.messageId);
    if (!message) throw new Error(`Message ${input.messageId} not found.`);
    if (!message.pinned) return { messageId: message.id, unpinned: true, note: 'Not pinned.' };

    await message.unpin(input.reason);

    return {
      messageId: message.id,
      unpinned: true,
    };
  },
};

export const purgeMessagesAction: ActionDefinition = {
  type: 'purge_messages',
  description: 'Bulk-deletes recent messages (max 100, skips pinned and older-than-14d).',
  inputSchema: z.object({
    channelId: z.string(),
    limit: z.number().int().min(1).max(100),
    userId: z.string().optional(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageMessages],
  requiredUserPermissions: [PermissionFlagsBits.ManageMessages],
  riskLevel: RiskLevel.HIGH,
  confirmationPolicy: ConfirmationPolicy.REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased() || !('bulkDelete' in channel)) {
      throw new Error(`Purgeable text channel ${input.channelId} not found.`);
    }

    const fetched = await channel.messages.fetch({ limit: input.limit });
    let targets = [...fetched.values()].filter((m) => !m.pinned);
    if (input.userId) {
      targets = targets.filter((m) => m.author.id === input.userId);
    }
    if (targets.length === 0) {
      return { channelId: channel.id, deleted: 0, note: 'No eligible messages found.' };
    }

    const deleted = await (channel as TextChannel).bulkDelete(targets, true);

    return {
      channelId: channel.id,
      deleted: deleted.size,
    };
  },
};

ActionRegistry.register(pinMessageAction);
ActionRegistry.register(unpinMessageAction);
ActionRegistry.register(purgeMessagesAction);
