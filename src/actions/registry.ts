import { ActionDefinition } from './types.js';
import * as schemas from './schemas.js';

export class ActionRegistry {
  private static actions: Map<string, ActionDefinition> = new Map();

  public static register(action: ActionDefinition): void {
    this.actions.set(action.type, action);
  }

  public static get(type: string): ActionDefinition | undefined {
    return this.actions.get(type);
  }

  public static getAll(): ActionDefinition[] {
    return Array.from(this.actions.values());
  }

  public static clear(): void {
    this.actions.clear();
  }
}

// Default Action Definitions
export const defaultActions: ActionDefinition[] = [
  // READ ACTIONS
  {
    type: 'get_server_info',
    description: 'Get general information about the Discord server',
    inputSchema: schemas.GetServerInfoSchema,
    requiredBotPermissions: [],
    requiredUserPermissions: [],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx) => ctx.discordAdapter.getGuildInfo(ctx.guildId),
  },
  {
    type: 'list_channels',
    description: 'List all channels in the server',
    inputSchema: schemas.ListChannelsSchema,
    requiredBotPermissions: [],
    requiredUserPermissions: [],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx) => ctx.discordAdapter.listChannels(ctx.guildId),
  },
  {
    type: 'get_channel',
    description: 'Get details of a specific channel',
    inputSchema: schemas.GetChannelSchema,
    requiredBotPermissions: [],
    requiredUserPermissions: [],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.getChannel(ctx.guildId, input.channelId),
  },
  {
    type: 'list_roles',
    description: 'List all roles in the server',
    inputSchema: schemas.ListRolesSchema,
    requiredBotPermissions: [],
    requiredUserPermissions: [],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx) => ctx.discordAdapter.listRoles(ctx.guildId),
  },
  {
    type: 'get_role',
    description: 'Get details of a specific role',
    inputSchema: schemas.GetRoleSchema,
    requiredBotPermissions: [],
    requiredUserPermissions: [],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.getRole(ctx.guildId, input.roleId),
  },
  {
    type: 'get_member',
    description: 'Get details of a server member',
    inputSchema: schemas.GetMemberSchema,
    requiredBotPermissions: [],
    requiredUserPermissions: [],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.getMember(ctx.guildId, input.userId),
  },

  // CHANNEL ACTIONS
  {
    type: 'create_channel',
    description: 'Create a new text or voice channel',
    inputSchema: schemas.CreateChannelSchema,
    requiredBotPermissions: ['MANAGE_CHANNELS'],
    requiredUserPermissions: ['MANAGE_CHANNELS'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => {
      const res = await ctx.discordAdapter.createChannel(ctx.guildId, input);
      ctx.createdResources?.push({ type: 'channel', id: res.id });
      return res;
    },
    rollback: async (ctx, resourceId) => {
      await ctx.discordAdapter.deleteChannel(ctx.guildId, resourceId);
    },
  },
  {
    type: 'edit_channel',
    description: 'Edit channel properties (name, topic, parent)',
    inputSchema: schemas.EditChannelSchema,
    requiredBotPermissions: ['MANAGE_CHANNELS'],
    requiredUserPermissions: ['MANAGE_CHANNELS'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.editChannel(ctx.guildId, input.channelId, input),
  },
  {
    type: 'delete_channel',
    description: 'Delete a channel permanently',
    inputSchema: schemas.DeleteChannelSchema,
    requiredBotPermissions: ['MANAGE_CHANNELS'],
    requiredUserPermissions: ['MANAGE_CHANNELS'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.deleteChannel(ctx.guildId, input.channelId),
  },
  {
    type: 'create_category',
    description: 'Create a new channel category',
    inputSchema: schemas.CreateCategorySchema,
    requiredBotPermissions: ['MANAGE_CHANNELS'],
    requiredUserPermissions: ['MANAGE_CHANNELS'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => {
      const res = await ctx.discordAdapter.createCategory(ctx.guildId, input.name);
      ctx.createdResources?.push({ type: 'channel', id: res.id });
      return res;
    },
    rollback: async (ctx, resourceId) => {
      await ctx.discordAdapter.deleteChannel(ctx.guildId, resourceId);
    },
  },
  {
    type: 'set_channel_permissions',
    description: 'Configure permission overwrites for a channel',
    inputSchema: schemas.SetChannelPermissionsSchema,
    requiredBotPermissions: ['MANAGE_CHANNELS', 'MANAGE_ROLES'],
    requiredUserPermissions: ['MANAGE_CHANNELS', 'MANAGE_ROLES'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.setChannelPermissions(ctx.guildId, input.channelId, input.overwrites),
  },

  // ROLE ACTIONS
  {
    type: 'create_role',
    description: 'Create a new server role',
    inputSchema: schemas.CreateRoleSchema,
    requiredBotPermissions: ['MANAGE_ROLES'],
    requiredUserPermissions: ['MANAGE_ROLES'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => {
      const res = await ctx.discordAdapter.createRole(ctx.guildId, input);
      ctx.createdResources?.push({ type: 'role', id: res.id });
      return res;
    },
    rollback: async (ctx, resourceId) => {
      await ctx.discordAdapter.deleteRole(ctx.guildId, resourceId);
    },
  },
  {
    type: 'edit_role',
    description: 'Edit a role name, color, or permissions',
    inputSchema: schemas.EditRoleSchema,
    requiredBotPermissions: ['MANAGE_ROLES'],
    requiredUserPermissions: ['MANAGE_ROLES'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.editRole(ctx.guildId, input.roleId, input),
  },
  {
    type: 'delete_role',
    description: 'Delete a role',
    inputSchema: schemas.DeleteRoleSchema,
    requiredBotPermissions: ['MANAGE_ROLES'],
    requiredUserPermissions: ['MANAGE_ROLES'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.deleteRole(ctx.guildId, input.roleId),
  },
  {
    type: 'assign_role',
    description: 'Assign a role to a member',
    inputSchema: schemas.AssignRoleSchema,
    requiredBotPermissions: ['MANAGE_ROLES'],
    requiredUserPermissions: ['MANAGE_ROLES'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.assignRole(ctx.guildId, input.userId, input.roleId),
  },
  {
    type: 'remove_role',
    description: 'Remove a role from a member',
    inputSchema: schemas.RemoveRoleSchema,
    requiredBotPermissions: ['MANAGE_ROLES'],
    requiredUserPermissions: ['MANAGE_ROLES'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.removeRole(ctx.guildId, input.userId, input.roleId),
  },

  // MEMBER / MODERATION ACTIONS
  {
    type: 'timeout_member',
    description: 'Timeout a member for a duration',
    inputSchema: schemas.TimeoutMemberSchema,
    requiredBotPermissions: ['MODERATE_MEMBERS'],
    requiredUserPermissions: ['MODERATE_MEMBERS'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.timeoutMember(ctx.guildId, input.userId, input.durationMs, input.reason),
  },
  {
    type: 'remove_timeout',
    description: 'Remove timeout from a member',
    inputSchema: schemas.RemoveTimeoutSchema,
    requiredBotPermissions: ['MODERATE_MEMBERS'],
    requiredUserPermissions: ['MODERATE_MEMBERS'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.removeTimeout(ctx.guildId, input.userId, input.reason),
  },
  {
    type: 'kick_member',
    description: 'Kick a member from the server',
    inputSchema: schemas.KickMemberSchema,
    requiredBotPermissions: ['KICK_MEMBERS'],
    requiredUserPermissions: ['KICK_MEMBERS'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.kickMember(ctx.guildId, input.userId, input.reason),
  },
  {
    type: 'ban_member',
    description: 'Ban a member from the server',
    inputSchema: schemas.BanMemberSchema,
    requiredBotPermissions: ['BAN_MEMBERS'],
    requiredUserPermissions: ['BAN_MEMBERS'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.banMember(ctx.guildId, input.userId, input.reason),
  },
  {
    type: 'unban_member',
    description: 'Unban a member',
    inputSchema: schemas.UnbanMemberSchema,
    requiredBotPermissions: ['BAN_MEMBERS'],
    requiredUserPermissions: ['BAN_MEMBERS'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.unbanMember(ctx.guildId, input.userId, input.reason),
  },
  {
    type: 'set_nickname',
    description: 'Set a member nickname',
    inputSchema: schemas.SetNicknameSchema,
    requiredBotPermissions: ['MANAGE_NICKNAMES'],
    requiredUserPermissions: ['MANAGE_NICKNAMES'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.setNickname(ctx.guildId, input.userId, input.nickname),
  },

  // MESSAGE ACTIONS
  {
    type: 'send_message',
    description: 'Send a message to a channel',
    inputSchema: schemas.SendMessageSchema,
    requiredBotPermissions: ['SEND_MESSAGES'],
    requiredUserPermissions: ['SEND_MESSAGES'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.sendMessage(ctx.guildId, input.channelId, input.content),
  },
  {
    type: 'edit_message',
    description: 'Edit a message sent by the bot',
    inputSchema: schemas.EditMessageSchema,
    requiredBotPermissions: ['SEND_MESSAGES'],
    requiredUserPermissions: ['SEND_MESSAGES'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.editMessage(ctx.guildId, input.channelId, input.messageId, input.content),
  },
  {
    type: 'delete_message',
    description: 'Delete a message in a channel',
    inputSchema: schemas.DeleteMessageSchema,
    requiredBotPermissions: ['MANAGE_MESSAGES'],
    requiredUserPermissions: ['MANAGE_MESSAGES'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.deleteMessage(ctx.guildId, input.channelId, input.messageId),
  },
  {
    type: 'pin_message',
    description: 'Pin a message in a channel',
    inputSchema: schemas.PinMessageSchema,
    requiredBotPermissions: ['MANAGE_MESSAGES'],
    requiredUserPermissions: ['MANAGE_MESSAGES'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.pinMessage(ctx.guildId, input.channelId, input.messageId),
  },
  {
    type: 'unpin_message',
    description: 'Unpin a message in a channel',
    inputSchema: schemas.UnpinMessageSchema,
    requiredBotPermissions: ['MANAGE_MESSAGES'],
    requiredUserPermissions: ['MANAGE_MESSAGES'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.unpinMessage(ctx.guildId, input.channelId, input.messageId),
  },
  {
    type: 'bulk_delete_messages',
    description: 'Bulk delete messages in a channel (2-100)',
    inputSchema: schemas.BulkDeleteSchema,
    requiredBotPermissions: ['MANAGE_MESSAGES'],
    requiredUserPermissions: ['MANAGE_MESSAGES'],
    riskLevel: 'HIGH',
    confirmationPolicy: 'REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.bulkDeleteMessages(ctx.guildId, input.channelId, input.count),
  },

  // THREAD ACTIONS
  {
    type: 'create_thread',
    description: 'Create a thread in a channel',
    inputSchema: schemas.CreateThreadSchema,
    requiredBotPermissions: ['CREATE_PUBLIC_THREADS'],
    requiredUserPermissions: ['CREATE_PUBLIC_THREADS'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.createThread(ctx.guildId, input.channelId, input),
  },
  {
    type: 'archive_thread',
    description: 'Archive a thread',
    inputSchema: schemas.ArchiveThreadSchema,
    requiredBotPermissions: ['MANAGE_THREADS'],
    requiredUserPermissions: ['MANAGE_THREADS'],
    riskLevel: 'LOW',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.archiveThread(ctx.guildId, input.threadId),
  },
  {
    type: 'lock_thread',
    description: 'Lock a thread',
    inputSchema: schemas.LockThreadSchema,
    requiredBotPermissions: ['MANAGE_THREADS'],
    requiredUserPermissions: ['MANAGE_THREADS'],
    riskLevel: 'MEDIUM',
    confirmationPolicy: 'NOT_REQUIRED',
    handler: async (ctx, input) => ctx.discordAdapter.lockThread(ctx.guildId, input.threadId),
  },
];

// Register default actions
defaultActions.forEach((act) => ActionRegistry.register(act));
