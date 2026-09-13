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

    const hierarchyCheck = HierarchyEngine.canBotManageMember(ctx.guild, member);
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

    const hierarchyCheck = HierarchyEngine.canBotManageMember(ctx.guild, member);
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
