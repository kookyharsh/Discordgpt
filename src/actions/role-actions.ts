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

export const deleteRoleAction: ActionDefinition = {
  type: 'delete_role',
  description: 'Deletes a role from the guild.',
  inputSchema: z.object({
    roleId: z.string(),
    reason: z.string().max(512).optional(),
  }),
  requiredBotPermissions: [PermissionFlagsBits.ManageRoles],
  requiredUserPermissions: [PermissionFlagsBits.ManageRoles],
  riskLevel: RiskLevel.HIGH,
  confirmationPolicy: ConfirmationPolicy.REQUIRED,
  handler: async (ctx, input) => {
    const role = await ctx.guild.roles.fetch(input.roleId);
    if (!role) throw new Error(`Role ${input.roleId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageRole(ctx.guild, role);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    const name = role.name;
    await role.delete(input.reason);

    return {
      roleId: input.roleId,
      name,
      deleted: true,
    };
  },
};

export const removeRoleAction: ActionDefinition = {
  type: 'remove_role',
  description: 'Removes a role from a guild member.',
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

    const member = await ctx.guild.members.fetch(input.memberId);
    if (!member) throw new Error(`Member ${input.memberId} not found.`);
    if (!member.roles.cache.has(role.id)) {
      return { memberId: member.id, roleId: role.id, removed: false, note: 'Member does not have this role.' };
    }

    await member.roles.remove(role);

    return {
      memberId: member.id,
      roleId: role.id,
      removed: true,
    };
  },
};

export const editRoleAction: ActionDefinition = {
  type: 'edit_role',
  description: 'Edits a role name, color, hoist, or mentionable flag.',
  inputSchema: z
    .object({
      roleId: z.string(),
      name: z.string().min(1).max(100).optional(),
      color: z.string().optional(),
      hoist: z.boolean().optional(),
      mentionable: z.boolean().optional(),
      reason: z.string().max(512).optional(),
    })
    .refine(
      (o) => o.name !== undefined || o.color !== undefined || o.hoist !== undefined || o.mentionable !== undefined,
      'Nothing to change: provide at least one of name, color, hoist, mentionable.'
    ),
  requiredBotPermissions: [PermissionFlagsBits.ManageRoles],
  requiredUserPermissions: [PermissionFlagsBits.ManageRoles],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const role = await ctx.guild.roles.fetch(input.roleId);
    if (!role) throw new Error(`Role ${input.roleId} not found.`);

    const hierarchyCheck = await HierarchyEngine.canBotManageRole(ctx.guild, role);
    if (!hierarchyCheck.allowed) {
      throw new Error(hierarchyCheck.reason);
    }

    const updated = await role.edit({
      ...(input.name !== undefined ? { name: input.name } : {}),
      ...(input.color !== undefined ? { color: input.color as any } : {}),
      ...(input.hoist !== undefined ? { hoist: input.hoist } : {}),
      ...(input.mentionable !== undefined ? { mentionable: input.mentionable } : {}),
      ...(input.reason !== undefined ? { reason: input.reason } : {}),
    });

    return {
      roleId: updated.id,
      name: updated.name,
    };
  },
};

ActionRegistry.register(deleteRoleAction);
ActionRegistry.register(removeRoleAction);
ActionRegistry.register(editRoleAction);
