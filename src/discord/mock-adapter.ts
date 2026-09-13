import {
  DiscordAdapter,
  GuildSummary,
  ChannelSummary,
  RoleSummary,
  MemberSummary,
  PermissionOverwriteInput,
} from './types.js';

export class MockDiscordAdapter implements DiscordAdapter {
  public guilds: Map<string, GuildSummary> = new Map();
  public channels: Map<string, ChannelSummary[]> = new Map();
  public roles: Map<string, RoleSummary[]> = new Map();
  public members: Map<string, MemberSummary[]> = new Map();
  public messages: Map<string, Array<{ id: string; channelId: string; content: any }>> = new Map();
  public botPermissions: Map<string, Set<string>> = new Map();

  constructor() {
    this.seedDefaultMockData();
  }

  public seedDefaultMockData() {
    const guildId = 'guild-123';
    this.guilds.set(guildId, {
      id: guildId,
      name: 'Test Server',
      memberCount: 100,
      features: ['COMMUNITY'],
    });

    this.channels.set(guildId, [
      { id: 'chan-1', name: 'general', type: 'GuildText', topic: 'General conversation' },
      { id: 'chan-2', name: 'announcements', type: 'GuildText', topic: 'Official news' },
      { id: 'chan-staff-1', name: 'staff', type: 'GuildText' },
      { id: 'chan-staff-2', name: 'staff-chat', type: 'GuildText' },
      { id: 'chan-staff-3', name: 'staff-only', type: 'GuildText' },
    ]);

    this.roles.set(guildId, [
      { id: 'role-everyone', name: '@everyone', position: 0, color: 0, permissions: '0', managed: false },
      { id: 'role-mod', name: 'Moderators', position: 5, color: 0x00ff00, permissions: '8', managed: false },
      { id: 'role-admin', name: 'Administrator', position: 10, color: 0xff0000, permissions: '8', managed: false },
    ]);

    this.members.set(guildId, [
      { id: 'user-admin', username: 'alice_admin', displayName: 'Alice', roles: ['role-admin'], highestRolePosition: 10, permissions: '8' },
      { id: 'user-mod', username: 'bob_mod', displayName: 'Bob', roles: ['role-mod'], highestRolePosition: 5, permissions: '4' },
      { id: 'user-regular', username: 'charlie_user', displayName: 'Charlie', roles: ['role-everyone'], highestRolePosition: 0, permissions: '0' },
      { id: 'bot-id', username: 'DiscordGPT', displayName: 'DiscordGPT', roles: ['role-admin'], highestRolePosition: 9, permissions: '8' },
    ]);

    this.botPermissions.set(guildId, new Set([
      'MANAGE_CHANNELS',
      'MANAGE_ROLES',
      'MODERATE_MEMBERS',
      'KICK_MEMBERS',
      'BAN_MEMBERS',
      'MANAGE_MESSAGES',
      'SEND_MESSAGES',
      'VIEW_CHANNEL',
    ]));
  }

  async getGuildInfo(guildId: string): Promise<GuildSummary> {
    const g = this.guilds.get(guildId);
    if (!g) throw new Error(`Guild ${guildId} not found`);
    return g;
  }

  async listChannels(guildId: string): Promise<ChannelSummary[]> {
    return this.channels.get(guildId) || [];
  }

  async getChannel(guildId: string, channelId: string): Promise<ChannelSummary | null> {
    const list = this.channels.get(guildId) || [];
    return list.find((c) => c.id === channelId || c.name === channelId) || null;
  }

  async listRoles(guildId: string): Promise<RoleSummary[]> {
    return this.roles.get(guildId) || [];
  }

  async getRole(guildId: string, roleId: string): Promise<RoleSummary | null> {
    const list = this.roles.get(guildId) || [];
    return list.find((r) => r.id === roleId || r.name === roleId) || null;
  }

  async getMember(guildId: string, userId: string): Promise<MemberSummary | null> {
    const list = this.members.get(guildId) || [];
    return list.find((m) => m.id === userId || m.username === userId || m.displayName === userId) || null;
  }

  async createChannel(guildId: string, options: { name: string; type?: number | string; parentId?: string; topic?: string }): Promise<ChannelSummary> {
    const list = this.channels.get(guildId) || [];
    const newChan: ChannelSummary = {
      id: `chan-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      name: options.name,
      type: String(options.type || 'GuildText'),
      parentId: options.parentId || null,
      topic: options.topic || null,
    };
    list.push(newChan);
    this.channels.set(guildId, list);
    return newChan;
  }

  async editChannel(guildId: string, channelId: string, options: { name?: string; topic?: string; parentId?: string }): Promise<ChannelSummary> {
    const list = this.channels.get(guildId) || [];
    const chan = list.find((c) => c.id === channelId);
    if (!chan) throw new Error(`Channel ${channelId} not found`);
    if (options.name !== undefined) chan.name = options.name;
    if (options.topic !== undefined) chan.topic = options.topic;
    if (options.parentId !== undefined) chan.parentId = options.parentId;
    return chan;
  }

  async deleteChannel(guildId: string, channelId: string): Promise<{ id: string; name: string }> {
    const list = this.channels.get(guildId) || [];
    const idx = list.findIndex((c) => c.id === channelId);
    if (idx === -1) throw new Error(`Channel ${channelId} not found`);
    const [deleted] = list.splice(idx, 1);
    return { id: deleted.id, name: deleted.name };
  }

  async createCategory(guildId: string, name: string): Promise<ChannelSummary> {
    return this.createChannel(guildId, { name, type: 'GuildCategory' });
  }

  async setChannelPermissions(guildId: string, channelId: string, overwrites: PermissionOverwriteInput[]): Promise<void> {
    const chan = await this.getChannel(guildId, channelId);
    if (!chan) throw new Error(`Channel ${channelId} not found`);
  }

  async createRole(guildId: string, options: { name: string; color?: number; permissions?: bigint | string[] }): Promise<RoleSummary> {
    const list = this.roles.get(guildId) || [];
    const newRole: RoleSummary = {
      id: `role-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      name: options.name,
      position: list.length + 1,
      color: options.color || 0,
      permissions: '0',
      managed: false,
    };
    list.push(newRole);
    this.roles.set(guildId, list);
    return newRole;
  }

  async editRole(guildId: string, roleId: string, options: { name?: string; color?: number; permissions?: bigint | string[] }): Promise<RoleSummary> {
    const list = this.roles.get(guildId) || [];
    const role = list.find((r) => r.id === roleId);
    if (!role) throw new Error(`Role ${roleId} not found`);
    if (options.name !== undefined) role.name = options.name;
    if (options.color !== undefined) role.color = options.color;
    return role;
  }

  async deleteRole(guildId: string, roleId: string): Promise<{ id: string; name: string }> {
    const list = this.roles.get(guildId) || [];
    const idx = list.findIndex((r) => r.id === roleId);
    if (idx === -1) throw new Error(`Role ${roleId} not found`);
    const [deleted] = list.splice(idx, 1);
    return { id: deleted.id, name: deleted.name };
  }

  async assignRole(guildId: string, userId: string, roleId: string): Promise<void> {
    const member = await this.getMember(guildId, userId);
    if (!member) throw new Error(`Member ${userId} not found`);
    if (!member.roles.includes(roleId)) member.roles.push(roleId);
  }

  async removeRole(guildId: string, userId: string, roleId: string): Promise<void> {
    const member = await this.getMember(guildId, userId);
    if (!member) throw new Error(`Member ${userId} not found`);
    member.roles = member.roles.filter((r) => r !== roleId);
  }

  async timeoutMember(guildId: string, userId: string, durationMs: number, reason?: string): Promise<void> {}
  async removeTimeout(guildId: string, userId: string, reason?: string): Promise<void> {}
  async kickMember(guildId: string, userId: string, reason?: string): Promise<void> {
    const list = this.members.get(guildId) || [];
    this.members.set(guildId, list.filter((m) => m.id !== userId));
  }
  async banMember(guildId: string, userId: string, reason?: string): Promise<void> {
    const list = this.members.get(guildId) || [];
    this.members.set(guildId, list.filter((m) => m.id !== userId));
  }
  async unbanMember(guildId: string, userId: string, reason?: string): Promise<void> {}
  async setNickname(guildId: string, userId: string, nickname: string): Promise<void> {
    const m = await this.getMember(guildId, userId);
    if (m) m.displayName = nickname;
  }

  async sendMessage(guildId: string, channelId: string, content: string | object): Promise<{ id: string; channelId: string }> {
    const list = this.messages.get(channelId) || [];
    const msg = { id: `msg-${Date.now()}`, channelId, content };
    list.push(msg);
    this.messages.set(channelId, list);
    return { id: msg.id, channelId };
  }

  async editMessage(guildId: string, channelId: string, messageId: string, content: string): Promise<void> {}
  async deleteMessage(guildId: string, channelId: string, messageId: string): Promise<void> {
    const list = this.messages.get(channelId) || [];
    this.messages.set(channelId, list.filter((m) => m.id !== messageId));
  }
  async pinMessage(guildId: string, channelId: string, messageId: string): Promise<void> {}
  async unpinMessage(guildId: string, channelId: string, messageId: string): Promise<void> {}
  async bulkDeleteMessages(guildId: string, channelId: string, count: number): Promise<{ deletedCount: number }> {
    return { deletedCount: count };
  }

  async createThread(guildId: string, channelId: string, options: { name: string; autoArchiveDuration?: number }): Promise<ChannelSummary> {
    return this.createChannel(guildId, { name: options.name, type: 'PublicThread', parentId: channelId });
  }
  async archiveThread(guildId: string, threadId: string): Promise<void> {}
  async lockThread(guildId: string, threadId: string): Promise<void> {}

  async checkBotPermissions(guildId: string, requiredPermissions: string[]): Promise<{ hasPermissions: boolean; missing: string[] }> {
    const current = this.botPermissions.get(guildId) || new Set();
    const missing = requiredPermissions.filter((p) => !current.has(p));
    return { hasPermissions: missing.length === 0, missing };
  }

  async checkUserPermissions(guildId: string, userId: string, requiredPermissions: string[], channelId?: string): Promise<{ hasPermissions: boolean; missing: string[] }> {
    const member = await this.getMember(guildId, userId);
    if (!member) return { hasPermissions: false, missing: requiredPermissions };
    if (member.id === 'user-admin' || member.roles.includes('role-admin')) {
      return { hasPermissions: true, missing: [] };
    }
    const missing = requiredPermissions.filter((p) => {
      if (p === 'BAN_MEMBERS' && member.roles.includes('role-mod')) return true;
      if (p === 'MANAGE_CHANNELS' && member.roles.includes('role-mod')) return true;
      return true;
    });
    return { hasPermissions: missing.length === 0, missing };
  }

  async checkRoleHierarchy(guildId: string, actorUserId: string, targetRoleId: string): Promise<boolean> {
    const actor = await this.getMember(guildId, actorUserId);
    const role = await this.getRole(guildId, targetRoleId);
    if (!actor || !role) return false;
    if (actor.roles.includes('role-admin')) return true;
    return actor.highestRolePosition > role.position;
  }

  async checkBotRoleHierarchy(guildId: string, targetRoleId: string): Promise<boolean> {
    const role = await this.getRole(guildId, targetRoleId);
    if (!role) return false;
    return 9 > role.position;
  }

  async checkMemberHierarchy(guildId: string, actorUserId: string, targetUserId: string): Promise<boolean> {
    const actor = await this.getMember(guildId, actorUserId);
    const target = await this.getMember(guildId, targetUserId);
    if (!actor || !target) return false;
    if (actor.roles.includes('role-admin')) return true;
    return actor.highestRolePosition > target.highestRolePosition;
  }

  async checkBotMemberHierarchy(guildId: string, targetUserId: string): Promise<boolean> {
    const target = await this.getMember(guildId, targetUserId);
    if (!target) return false;
    return 9 > target.highestRolePosition;
  }
}
