import {
  Client,
  GatewayIntentBits,
  ChannelType,
  PermissionsBitField,
  Guild,
  TextChannel,
  Role,
  GuildMember,
} from 'discord.js';
import {
  DiscordAdapter,
  GuildSummary,
  ChannelSummary,
  RoleSummary,
  MemberSummary,
  PermissionOverwriteInput,
} from './types.js';

export class LiveDiscordAdapter implements DiscordAdapter {
  constructor(private client: Client) {}

  private async getGuild(guildId: string): Promise<Guild> {
    const guild = await this.client.guilds.fetch(guildId).catch(() => null);
    if (!guild) {
      throw new Error(`Guild ${guildId} not found or bot is not a member.`);
    }
    return guild;
  }

  async getGuildInfo(guildId: string): Promise<GuildSummary> {
    const guild = await this.getGuild(guildId);
    return {
      id: guild.id,
      name: guild.name,
      memberCount: guild.memberCount,
      features: [...guild.features],
    };
  }

  async listChannels(guildId: string): Promise<ChannelSummary[]> {
    const guild = await this.getGuild(guildId);
    const channels = await guild.channels.fetch();
    return channels
      .filter((c): c is NonNullable<typeof c> => c !== null)
      .map((c) => ({
        id: c.id,
        name: c.name,
        type: ChannelType[c.type] ?? String(c.type),
        parentId: c.parentId,
        topic: 'topic' in c ? (c.topic as string | null) : null,
      }));
  }

  async getChannel(guildId: string, channelId: string): Promise<ChannelSummary | null> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId).catch(() => null);
    if (!channel) return null;
    return {
      id: channel.id,
      name: channel.name,
      type: ChannelType[channel.type] ?? String(channel.type),
      parentId: channel.parentId,
      topic: 'topic' in channel ? (channel.topic as string | null) : null,
    };
  }

  async listRoles(guildId: string): Promise<RoleSummary[]> {
    const guild = await this.getGuild(guildId);
    const roles = await guild.roles.fetch();
    return Array.from(roles.values()).map((r) => ({
      id: r.id,
      name: r.name,
      position: r.position,
      color: r.color,
      permissions: r.permissions.bitfield.toString(),
      managed: r.managed,
    }));
  }

  async getRole(guildId: string, roleId: string): Promise<RoleSummary | null> {
    const guild = await this.getGuild(guildId);
    const role = await guild.roles.fetch(roleId).catch(() => null);
    if (!role) return null;
    return {
      id: role.id,
      name: role.name,
      position: role.position,
      color: role.color,
      permissions: role.permissions.bitfield.toString(),
      managed: role.managed,
    };
  }

  async getMember(guildId: string, userId: string): Promise<MemberSummary | null> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId).catch(() => null);
    if (!member) return null;
    return {
      id: member.id,
      username: member.user.username,
      displayName: member.displayName,
      roles: Array.from(member.roles.cache.keys()),
      highestRolePosition: member.roles.highest.position,
      permissions: member.permissions.bitfield.toString(),
    };
  }

  async createChannel(
    guildId: string,
    options: { name: string; type?: number | string; parentId?: string; topic?: string }
  ): Promise<ChannelSummary> {
    const guild = await this.getGuild(guildId);
    const type = typeof options.type === 'number' ? options.type : ChannelType.GuildText;
    const created = await guild.channels.create({
      name: options.name,
      type: type as any,
      parent: options.parentId,
      topic: options.topic,
    });
    return {
      id: created.id,
      name: created.name,
      type: ChannelType[created.type] ?? String(created.type),
      parentId: created.parentId,
      topic: 'topic' in created ? (created.topic as string | null) : null,
    };
  }

  async editChannel(
    guildId: string,
    channelId: string,
    options: { name?: string; topic?: string; parentId?: string }
  ): Promise<ChannelSummary> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel) throw new Error(`Channel ${channelId} not found.`);
    const updated = await channel.edit({
      name: options.name,
      topic: options.topic,
      parent: options.parentId,
    });
    return {
      id: updated.id,
      name: updated.name,
      type: ChannelType[updated.type] ?? String(updated.type),
      parentId: updated.parentId,
      topic: 'topic' in updated ? (updated.topic as string | null) : null,
    };
  }

  async deleteChannel(guildId: string, channelId: string): Promise<{ id: string; name: string }> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel) throw new Error(`Channel ${channelId} not found.`);
    const name = channel.name;
    await channel.delete();
    return { id: channelId, name };
  }

  async createCategory(guildId: string, name: string): Promise<ChannelSummary> {
    return this.createChannel(guildId, { name, type: ChannelType.GuildCategory });
  }

  async setChannelPermissions(
    guildId: string,
    channelId: string,
    overwrites: PermissionOverwriteInput[]
  ): Promise<void> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('permissionOverwrites' in channel)) {
      throw new Error(`Channel ${channelId} does not support permission overwrites.`);
    }

    const formattedOverwrites = overwrites.map((o) => ({
      id: o.targetId,
      allow: Array.isArray(o.allow)
        ? o.allow.map((p) => (PermissionsBitField.Flags as any)[p])
        : o.allow,
      deny: Array.isArray(o.deny)
        ? o.deny.map((p) => (PermissionsBitField.Flags as any)[p])
        : o.deny,
    }));

    await channel.permissionOverwrites.set(formattedOverwrites as any);
  }

  async createRole(
    guildId: string,
    options: { name: string; color?: number; permissions?: bigint | string[] }
  ): Promise<RoleSummary> {
    const guild = await this.getGuild(guildId);
    const perms = Array.isArray(options.permissions)
      ? options.permissions.map((p) => (PermissionsBitField.Flags as any)[p])
      : options.permissions;

    const role = await guild.roles.create({
      name: options.name,
      color: options.color,
      permissions: perms as any,
    });
    return {
      id: role.id,
      name: role.name,
      position: role.position,
      color: role.color,
      permissions: role.permissions.bitfield.toString(),
      managed: role.managed,
    };
  }

  async editRole(
    guildId: string,
    roleId: string,
    options: { name?: string; color?: number; permissions?: bigint | string[] }
  ): Promise<RoleSummary> {
    const guild = await this.getGuild(guildId);
    const role = await guild.roles.fetch(roleId);
    if (!role) throw new Error(`Role ${roleId} not found.`);
    const perms = Array.isArray(options.permissions)
      ? options.permissions.map((p) => (PermissionsBitField.Flags as any)[p])
      : options.permissions;
    const updated = await role.edit({
      name: options.name,
      color: options.color,
      permissions: perms as any,
    });
    return {
      id: updated.id,
      name: updated.name,
      position: updated.position,
      color: updated.color,
      permissions: updated.permissions.bitfield.toString(),
      managed: updated.managed,
    };
  }

  async deleteRole(guildId: string, roleId: string): Promise<{ id: string; name: string }> {
    const guild = await this.getGuild(guildId);
    const role = await guild.roles.fetch(roleId);
    if (!role) throw new Error(`Role ${roleId} not found.`);
    const name = role.name;
    await role.delete();
    return { id: roleId, name };
  }

  async assignRole(guildId: string, userId: string, roleId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId);
    await member.roles.add(roleId);
  }

  async removeRole(guildId: string, userId: string, roleId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId);
    await member.roles.remove(roleId);
  }

  async timeoutMember(guildId: string, userId: string, durationMs: number, reason?: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId);
    await member.timeout(durationMs, reason);
  }

  async removeTimeout(guildId: string, userId: string, reason?: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId);
    await member.timeout(null, reason);
  }

  async kickMember(guildId: string, userId: string, reason?: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId);
    await member.kick(reason);
  }

  async banMember(guildId: string, userId: string, reason?: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    await guild.members.ban(userId, { reason });
  }

  async unbanMember(guildId: string, userId: string, reason?: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    await guild.members.unban(userId, reason);
  }

  async setNickname(guildId: string, userId: string, nickname: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId);
    await member.setNickname(nickname);
  }

  async sendMessage(guildId: string, channelId: string, content: string | object): Promise<{ id: string; channelId: string }> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('send' in channel)) {
      throw new Error(`Channel ${channelId} cannot receive messages.`);
    }
    const msgPayload = typeof content === 'string' ? { content } : (content as any);
    const sent = await (channel as TextChannel).send(msgPayload);
    return { id: sent.id, channelId: sent.channelId };
  }

  async editMessage(guildId: string, channelId: string, messageId: string, content: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('messages' in channel)) throw new Error(`Channel ${channelId} message fetch unavailable.`);
    const msg = await (channel as TextChannel).messages.fetch(messageId);
    await msg.edit(content);
  }

  async deleteMessage(guildId: string, channelId: string, messageId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('messages' in channel)) throw new Error(`Channel ${channelId} message fetch unavailable.`);
    const msg = await (channel as TextChannel).messages.fetch(messageId);
    await msg.delete();
  }

  async pinMessage(guildId: string, channelId: string, messageId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('messages' in channel)) throw new Error(`Channel ${channelId} message fetch unavailable.`);
    const msg = await (channel as TextChannel).messages.fetch(messageId);
    await msg.pin();
  }

  async unpinMessage(guildId: string, channelId: string, messageId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('messages' in channel)) throw new Error(`Channel ${channelId} message fetch unavailable.`);
    const msg = await (channel as TextChannel).messages.fetch(messageId);
    await msg.unpin();
  }

  async bulkDeleteMessages(guildId: string, channelId: string, count: number): Promise<{ deletedCount: number }> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('bulkDelete' in channel)) throw new Error(`Channel ${channelId} does not support bulk delete.`);
    const deleted = await (channel as TextChannel).bulkDelete(count, true);
    return { deletedCount: deleted.size };
  }

  async createThread(guildId: string, channelId: string, options: { name: string; autoArchiveDuration?: number }): Promise<ChannelSummary> {
    const guild = await this.getGuild(guildId);
    const channel = await guild.channels.fetch(channelId);
    if (!channel || !('threads' in channel)) throw new Error(`Channel ${channelId} does not support threads.`);
    const thread = await (channel as TextChannel).threads.create({
      name: options.name,
      autoArchiveDuration: options.autoArchiveDuration,
    });
    return {
      id: thread.id,
      name: thread.name,
      type: ChannelType[thread.type] ?? String(thread.type),
      parentId: thread.parentId,
      topic: null,
    };
  }

  async archiveThread(guildId: string, threadId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const thread = await guild.channels.fetch(threadId);
    if (!thread || !thread.isThread()) throw new Error(`Thread ${threadId} not found.`);
    await thread.setArchived(true);
  }

  async lockThread(guildId: string, threadId: string): Promise<void> {
    const guild = await this.getGuild(guildId);
    const thread = await guild.channels.fetch(threadId);
    if (!thread || !thread.isThread()) throw new Error(`Thread ${threadId} not found.`);
    await thread.setLocked(true);
  }

  async checkBotPermissions(guildId: string, requiredPermissions: string[]): Promise<{ hasPermissions: boolean; missing: string[] }> {
    const guild = await this.getGuild(guildId);
    const me = await guild.members.fetchMe();
    const missing: string[] = [];

    for (const perm of requiredPermissions) {
      const flag = (PermissionsBitField.Flags as any)[perm];
      if (flag && !me.permissions.has(flag)) {
        missing.push(perm);
      }
    }
    return { hasPermissions: missing.length === 0, missing };
  }

  async checkUserPermissions(guildId: string, userId: string, requiredPermissions: string[], channelId?: string): Promise<{ hasPermissions: boolean; missing: string[] }> {
    const guild = await this.getGuild(guildId);
    const member = await guild.members.fetch(userId).catch(() => null);
    if (!member) return { hasPermissions: false, missing: requiredPermissions };

    if (guild.ownerId === userId) {
      return { hasPermissions: true, missing: [] };
    }

    let perms = member.permissions;
    if (channelId) {
      const channel = await guild.channels.fetch(channelId).catch(() => null);
      if (channel) perms = member.permissionsIn(channel);
    }

    const missing: string[] = [];
    for (const perm of requiredPermissions) {
      const flag = (PermissionsBitField.Flags as any)[perm];
      if (flag && !perms.has(flag)) {
        missing.push(perm);
      }
    }
    return { hasPermissions: missing.length === 0, missing };
  }

  async checkRoleHierarchy(guildId: string, actorUserId: string, targetRoleId: string): Promise<boolean> {
    const guild = await this.getGuild(guildId);
    if (guild.ownerId === actorUserId) return true;
    const actor = await guild.members.fetch(actorUserId).catch(() => null);
    const targetRole = await guild.roles.fetch(targetRoleId).catch(() => null);
    if (!actor || !targetRole) return false;
    return actor.roles.highest.position > targetRole.position;
  }

  async checkBotRoleHierarchy(guildId: string, targetRoleId: string): Promise<boolean> {
    const guild = await this.getGuild(guildId);
    const bot = await guild.members.fetchMe();
    const targetRole = await guild.roles.fetch(targetRoleId).catch(() => null);
    if (!bot || !targetRole) return false;
    return bot.roles.highest.position > targetRole.position;
  }

  async checkMemberHierarchy(guildId: string, actorUserId: string, targetUserId: string): Promise<boolean> {
    const guild = await this.getGuild(guildId);
    if (guild.ownerId === actorUserId) return true;
    if (guild.ownerId === targetUserId) return false;
    const actor = await guild.members.fetch(actorUserId).catch(() => null);
    const target = await guild.members.fetch(targetUserId).catch(() => null);
    if (!actor || !target) return false;
    return actor.roles.highest.position > target.roles.highest.position;
  }

  async checkBotMemberHierarchy(guildId: string, targetUserId: string): Promise<boolean> {
    const guild = await this.getGuild(guildId);
    if (guild.ownerId === targetUserId) return false;
    const bot = await guild.members.fetchMe();
    const target = await guild.members.fetch(targetUserId).catch(() => null);
    if (!bot || !target) return false;
    return bot.roles.highest.position > target.roles.highest.position;
  }
}
