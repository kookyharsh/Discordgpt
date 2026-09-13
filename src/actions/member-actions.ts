import { z } from 'zod';
import { PermissionFlagsBits } from 'discord.js';
import { ActionDefinition, ConfirmationPolicy, RiskLevel } from './types.js';
import { ActionRegistry } from './registry.js';
import { HierarchyEngine } from '../permissions/permission-engine.js';

export const timeoutMemberAction: ActionDefinition = {
  type: 'timeout_member',
  description: 'Times out a member for a given duration in seconds.',
  inputSchema: z.object({
    memberId: z.string(),
    durationSeconds: z.number().min(1).max(28 * 24 * 3600),
    reason: z.string().optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ModerateMembers],
  requiredUserPermissions: [PermissionFlagsBits.ModerateMembers],
  riskLevel: RiskLevel.MEDIUM,
  confirmationPolicy: ConfirmationPolicy.REQUIRED,
  handler: async (ctx, input) => {
    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageMember(ctx.guild, member);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    await member.timeout(input.durationSeconds * 1000, input.reason);

    return {
      memberId: member.id,
      durationSeconds: input.durationSeconds,
      timedOut: true,
    };
  },
};

export const banMemberAction: ActionDefinition = {
  type: 'ban_member',
  description: 'Bans a member from the guild.',
  inputSchema: z.object({
    memberId: z.string(),
    reason: z.string().optional(),
    deleteMessageSeconds: z.number().optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.BanMembers],
  requiredUserPermissions: [PermissionFlagsBits.BanMembers],
  riskLevel: RiskLevel.HIGH,
  confirmationPolicy: ConfirmationPolicy.REQUIRED,
  handler: async (ctx, input) => {
    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageMember(ctx.guild, member);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    await member.ban({
      reason: input.reason,
      deleteMessageSeconds: input.deleteMessageSeconds,
    });

    return {
      memberId: input.memberId,
      banned: true,
    };
  },
};

ActionRegistry.register(timeoutMemberAction);
ActionRegistry.register(banMemberAction);

export const kickMemberAction: ActionDefinition = {
  type: 'kick_member',
  description: 'Kicks a member from the guild (they can rejoin with a new invite).',
  inputSchema: z.object({
    memberId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.KickMembers],
  requiredUserPermissions: [PermissionFlagsBits.KickMembers],
  riskLevel: RiskLevel.HIGH,
  confirmationPolicy: ConfirmationPolicy.REQUIRED,
  handler: async (ctx, input) => {
    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageMember(ctx.guild, member);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    await member.kick(input.reason);

    return {
      memberId: member.id,
      kicked: true,
    };
  },
};

export const unbanMemberAction: ActionDefinition = {
  type: 'unban_member',
  description: 'Unbans a user by ID so they can rejoin the guild.',
  inputSchema: z.object({
    userId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.BanMembers],
  requiredUserPermissions: [PermissionFlagsBits.BanMembers],
  riskLevel: RiskLevel.MEDIUM,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    await ctx.guild.bans.remove(input.userId, input.reason);

    return {
      userId: input.userId,
      unbanned: true,
    };
  },
};

export const untimeoutMemberAction: ActionDefinition = {
  type: 'untimeout_member',
  description: 'Removes an active timeout from a member.',
  inputSchema: z.object({
    memberId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ModerateMembers],
  requiredUserPermissions: [PermissionFlagsBits.ModerateMembers],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);
    if (!member.communicationDisabledUntil) {
      return { memberId: member.id, untimedOut: false, note: 'Member is not timed out.' };
    }

    await member.timeout(null, input.reason);

    return {
      memberId: member.id,
      untimedOut: true,
    };
  },
};

export const setNicknameAction: ActionDefinition = {
  type: 'set_nickname',
  description: 'Sets or clears a member nickname (empty nickname clears it).',
  inputSchema: z.object({
    memberId: z.string(),
    nickname: z.string().max(32).optional(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageNicknames],
  requiredUserPermissions: [PermissionFlagsBits.ManageNicknames],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageMember(ctx.guild, member);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    const nickname = input.nickname?.trim() ? input.nickname.trim() : null;
    await member.setNickname(nickname, input.reason);

    return {
      memberId: member.id,
      nickname,
    };
  },
};

export const moveMemberAction: ActionDefinition = {
  type: 'move_member',
  description: 'Moves a member to a voice channel, or disconnects them when no channel is given.',
  inputSchema: z.object({
    memberId: z.string(),
    channelId: z.string().optional(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.MoveMembers],
  requiredUserPermissions: [PermissionFlagsBits.MoveMembers],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);
    if (!member.voice.channel) {
      throw new Error(`${member.user.tag} is not in a voice channel.`);
    }

    if (input.channelId) {
      const target = await ctx.guild.channels.fetch(input.channelId);
      if (!target || !target.isVoiceBased()) {
        throw new Error(`Voice channel ${input.channelId} not found.`);
      }
      await member.voice.setChannel(target.id, input.reason);
    } else {
      await member.voice.disconnect(input.reason);
    }

    return {
      memberId: member.id,
      channelId: input.channelId ?? null,
      moved: true,
    };
  },
};

ActionRegistry.register(kickMemberAction);
ActionRegistry.register(unbanMemberAction);
ActionRegistry.register(untimeoutMemberAction);
ActionRegistry.register(setNicknameAction);
ActionRegistry.register(moveMemberAction);
