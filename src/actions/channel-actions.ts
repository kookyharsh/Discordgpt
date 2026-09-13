import { z } from 'zod';
import { ChannelType, PermissionFlagsBits } from 'discord.js';
import { ActionDefinition, ConfirmationPolicy, RiskLevel } from './types.js';
import { ActionRegistry } from './registry.js';

export const createChannelAction: ActionDefinition = {
  type: 'create_channel',
  description: 'Creates a new text or voice channel in the guild.',
  inputSchema: z.object({
    name: z.string().min(1).max(100),
    type: z.enum(['text', 'voice', 'category']).default('text'),
    categoryId: z.string().optional(),
    topic: z.string().max(1024).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channelType =
      input.type === 'category'
        ? ChannelType.GuildCategory
        : input.type === 'voice'
        ? ChannelType.GuildVoice
        : ChannelType.GuildText;

    const channel = await ctx.guild.channels.create({
      name: input.name,
      type: channelType,
      parent: input.categoryId,
      topic: input.topic,
    });

    return {
      channelId: channel.id,
      name: channel.name,
      type: input.type,
    };
  },
};

export const deleteChannelAction: ActionDefinition = {
  type: 'delete_channel',
  description: 'Deletes a channel from the guild.',
  inputSchema: z.object({
    channelId: z.string(),
    reason: z.string().optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.HIGH,
  confirmationPolicy: ConfirmationPolicy.REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel) {
      throw new Error(`Channel with ID ${input.channelId} not found.`);
    }

    const channelName = channel.name;
    await channel.delete(input.reason);

    return {
      channelId: input.channelId,
      name: channelName,
      deleted: true,
    };
  },
};

ActionRegistry.register(createChannelAction);
ActionRegistry.register(deleteChannelAction);
