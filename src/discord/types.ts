import { PermissionFlagsBits } from 'discord.js';

export interface EntitySummary {
  id: string;
  name: string;
  type: string;
}

export interface GuildSummary {
  id: string;
  name: string;
  memberCount: number;
  features: string[];
}

export interface ChannelSummary {
  id: string;
  name: string;
  type: string;
  parentId?: string | null;
  topic?: string | null;
}

export interface RoleSummary {
  id: string;
  name: string;
  position: number;
  color: number;
  permissions: string;
  managed: boolean;
}

export interface MemberSummary {
  id: string;
  username: string;
  displayName: string;
  roles: string[];
  highestRolePosition: number;
  permissions: string;
}

export interface PermissionOverwriteInput {
  targetId: string;
  targetType: 'role' | 'member';
  allow?: bigint | string[];
  deny?: bigint | string[];
}

export interface DiscordAdapter {
  getGuildInfo(guildId: string): Promise<GuildSummary>;
  listChannels(guildId: string): Promise<ChannelSummary[]>;
  getChannel(guildId: string, channelId: string): Promise<ChannelSummary | null>;
  listRoles(guildId: string): Promise<RoleSummary[]>;
  getRole(guildId: string, roleId: string): Promise<RoleSummary | null>;
  getMember(guildId: string, userId: string): Promise<MemberSummary | null>;

  createChannel(guildId: string, options: { name: string; type?: number | string; parentId?: string; topic?: string }): Promise<ChannelSummary>;
  editChannel(guildId: string, channelId: string, options: { name?: string; topic?: string; parentId?: string }): Promise<ChannelSummary>;
  deleteChannel(guildId: string, channelId: string): Promise<{ id: string; name: string }>;
  createCategory(guildId: string, name: string): Promise<ChannelSummary>;
  setChannelPermissions(guildId: string, channelId: string, overwrites: PermissionOverwriteInput[]): Promise<void>;

  createRole(guildId: string, options: { name: string; color?: number; permissions?: bigint | string[] }): Promise<RoleSummary>;
  editRole(guildId: string, roleId: string, options: { name?: string; color?: number; permissions?: bigint | string[] }): Promise<RoleSummary>;
  deleteRole(guildId: string, roleId: string): Promise<{ id: string; name: string }>;
  assignRole(guildId: string, userId: string, roleId: string): Promise<void>;
  removeRole(guildId: string, userId: string, roleId: string): Promise<void>;

  timeoutMember(guildId: string, userId: string, durationMs: number, reason?: string): Promise<void>;
  removeTimeout(guildId: string, userId: string, reason?: string): Promise<void>;
  kickMember(guildId: string, userId: string, reason?: string): Promise<void>;
  banMember(guildId: string, userId: string, reason?: string): Promise<void>;
  unbanMember(guildId: string, userId: string, reason?: string): Promise<void>;
  setNickname(guildId: string, userId: string, nickname: string): Promise<void>;

  sendMessage(guildId: string, channelId: string, content: string | object): Promise<{ id: string; channelId: string }>;
  editMessage(guildId: string, channelId: string, messageId: string, content: string): Promise<void>;
  deleteMessage(guildId: string, channelId: string, messageId: string): Promise<void>;
  pinMessage(guildId: string, channelId: string, messageId: string): Promise<void>;
  unpinMessage(guildId: string, channelId: string, messageId: string): Promise<void>;
  bulkDeleteMessages(guildId: string, channelId: string, count: number): Promise<{ deletedCount: number }>;

  createThread(guildId: string, channelId: string, options: { name: string; autoArchiveDuration?: number }): Promise<ChannelSummary>;
  archiveThread(guildId: string, threadId: string): Promise<void>;
  lockThread(guildId: string, threadId: string): Promise<void>;

  checkBotPermissions(guildId: string, requiredPermissions: string[]): Promise<{ hasPermissions: boolean; missing: string[] }>;
  checkUserPermissions(guildId: string, userId: string, requiredPermissions: string[], channelId?: string): Promise<{ hasPermissions: boolean; missing: string[] }>;
  checkRoleHierarchy(guildId: string, actorUserId: string, targetRoleId: string): Promise<boolean>;
  checkBotRoleHierarchy(guildId: string, targetRoleId: string): Promise<boolean>;
  checkMemberHierarchy(guildId: string, actorUserId: string, targetUserId: string): Promise<boolean>;
  checkBotMemberHierarchy(guildId: string, targetUserId: string): Promise<boolean>;
}
