import { z } from 'zod';
import { PermissionFlagsBits } from 'discord.js';
import { ActionDefinition, ConfirmationPolicy, RiskLevel } from './types.js';
import { ActionRegistry } from './registry.js';
import { HierarchyEngine } from '../permissions/permission-engine.js';

export const createRoleAction: ActionDefinition = {
  type: 'create_role',
  description: 'Creates a new role in the guild.',
  inputSchema: z.object({
    name: z.string().min(1).max(100),
    color: z.string().optional(),
    hoist: z.boolean().optional(),
    mentionable: z.boolean().optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageRoles],
  requiredUserPermissions: [PermissionFlagsBits.ManageRoles],
  riskLevel: RiskLevel.MEDIUM,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const role = await ctx.guild.roles.create({
      name: input.name,
      color: input.color as any,
      hoist: input.hoist,
      mentionable: input.mentionable,
    });

    return {
      roleId: role.id,
      name: role.name,
    };
  },
};

export const assignRoleAction: ActionDefinition = {
  type: 'assign_role',
  description: 'Assigns a role to a guild member.',
  inputSchema: z.object({
    memberId: z.string(),
    roleId: z.string(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageRoles],
  requiredUserPermissions: [PermissionFlagsBits.ManageRoles],
  riskLevel: RiskLevel.MEDIUM,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const role = await ctx.guild.roles.fetch(input.roleId);
    if (!role) throw new Error(`Role ${input.roleId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageRole(ctx.guild, role);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);

    await member.roles.add(role);

    return {
      memberId: member.id,
      roleId: role.id,
      assigned: true,
    };
  },
};

ActionRegistry.register(createRoleAction);
ActionRegistry.register(assignRoleAction);
