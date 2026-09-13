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

export const setSlowmodeAction: ActionDefinition = {
  type: 'set_slowmode',
  description: 'Sets slowmode delay in seconds on a text channel (0 disables).',
  inputSchema: z.object({
    channelId: z.string(),
    seconds: z.number().int().min(0).max(21600),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased() || channel.isDMBased()) {
      throw new Error(`Text channel ${input.channelId} not found.`);
    }
    if (!('setRateLimitPerUser' in channel)) {
      throw new Error('Slowmode is not supported in this channel type.');
    }

    await (channel as any).setRateLimitPerUser(input.seconds, input.reason);

    return {
      channelId: channel.id,
      seconds: input.seconds,
    };
  },
};

export const lockChannelAction: ActionDefinition = {
  type: 'lock_channel',
  description: 'Locks a channel by denying Send Messages for @everyone.',
  inputSchema: z.object({
    channelId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels, PermissionFlagsBits.ManageRoles],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.MEDIUM,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || channel.isDMBased() || !('permissionOverwrites' in channel)) {
      throw new Error(`Guild channel ${input.channelId} not found.`);
    }

    await (channel as any).permissionOverwrites.edit(
      ctx.guild.roles.everyone,
      { SendMessages: false },
      { reason: input.reason }
    );

    return {
      channelId: channel.id,
      locked: true,
    };
  },
};

export const unlockChannelAction: ActionDefinition = {
  type: 'unlock_channel',
  description: 'Unlocks a channel by resetting the @everyone Send Messages overwrite to neutral.',
  inputSchema: z.object({
    channelId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels, PermissionFlagsBits.ManageRoles],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || channel.isDMBased() || !('permissionOverwrites' in channel)) {
      throw new Error(`Guild channel ${input.channelId} not found.`);
    }

    await (channel as any).permissionOverwrites.edit(
      ctx.guild.roles.everyone,
      { SendMessages: null },
      { reason: input.reason }
    );

    return {
      channelId: channel.id,
      locked: false,
    };
  },
};

export const renameChannelAction: ActionDefinition = {
  type: 'rename_channel',
  description: 'Renames a channel.',
  inputSchema: z.object({
    channelId: z.string(),
    newName: z.string().min(1).max(100),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || channel.isDMBased() || !('setName' in channel)) {
      throw new Error(`Renamable channel ${input.channelId} not found.`);
    }

    await (channel as any).setName(input.newName, input.reason);

    return {
      channelId: channel.id,
      newName: input.newName,
    };
  },
};

export const setChannelTopicAction: ActionDefinition = {
  type: 'set_topic',
  description: 'Sets a text channel topic (empty clears it).',
  inputSchema: z.object({
    channelId: z.string(),
    topic: z.string().max(1024).optional(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageChannels],
  requiredUserPermissions: [PermissionFlagsBits.ManageChannels],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased() || channel.isDMBased() || !('setTopic' in channel)) {
      throw new Error(`Topic-capable text channel ${input.channelId} not found.`);
    }

    await (channel as any).setTopic(input.topic?.trim() ? input.topic : null, input.reason);

    return {
      channelId: channel.id,
      topic: input.topic ?? null,
    };
  },
};

ActionRegistry.register(setSlowmodeAction);
ActionRegistry.register(lockChannelAction);
ActionRegistry.register(unlockChannelAction);
ActionRegistry.register(renameChannelAction);
ActionRegistry.register(setChannelTopicAction);
