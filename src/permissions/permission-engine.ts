import { GuildMember, PermissionFlagsBits, Role, Guild } from 'discord.js';

export interface PermissionCheckResult {
  allowed: boolean;
  missingPermissions: string[];
  reason?: string;
}

export class PermissionEngine {
  static checkBotPermissions(
    guild: Guild,
    requiredPermissions: bigint[]
  ): PermissionCheckResult {
    const botMember = guild.members.me;
    if (!botMember) {
      return {
        allowed: false,
        missingPermissions: [],
        reason: 'Bot member object is not present in the guild context.',
      };
    }

    const missing: string[] = [];
    for (const perm of requiredPermissions) {
      if (!botMember.permissions.has(perm)) {
        const permName = Object.keys(PermissionFlagsBits).find(
          (key) => (PermissionFlagsBits as any)[key] === perm
        ) || perm.toString();
        missing.push(permName);
      }
    }

    if (missing.length > 0) {
      return {
        allowed: false,
        missingPermissions: missing,
        reason: `Bot lacks required permission(s): ${missing.join(', ')}`,
      };
    }

    return { allowed: true, missingPermissions: [] };
  }

  static checkUserPermissions(
    member: GuildMember,
    requiredPermissions: bigint[]
  ): PermissionCheckResult {
    const missing: string[] = [];
    for (const perm of requiredPermissions) {
      if (!member.permissions.has(perm)) {
        const permName = Object.keys(PermissionFlagsBits).find(
          (key) => (PermissionFlagsBits as any)[key] === perm
        ) || perm.toString();
        missing.push(permName);
      }
    }

    if (missing.length > 0) {
      return {
        allowed: false,
        missingPermissions: missing,
        reason: `User ${member.user.tag} lacks required permission(s): ${missing.join(', ')}`,
      };
    }

    return { allowed: true, missingPermissions: [] };
  }
}

export class HierarchyEngine {
  static canActorManageMember(actor: GuildMember, target: GuildMember): boolean {
    if (actor.guild.ownerId === actor.id) return true;
    if (target.guild.ownerId === target.id) return false;
    return actor.roles.highest.position > target.roles.highest.position;
  }

  static canActorManageRole(actor: GuildMember, targetRole: Role): boolean {
    if (actor.guild.ownerId === actor.id) return true;
    if (targetRole.managed) return false;
    return actor.roles.highest.position > targetRole.position;
  }

  static canBotManageRole(guild: Guild, targetRole: Role): { allowed: boolean; reason?: string } {
    const botMember = guild.members.me;
    if (!botMember) return { allowed: false, reason: 'Bot member not found.' };

    if (targetRole.managed) {
      return { allowed: false, reason: `Role @${targetRole.name} is managed by an integration.` };
    }

    if (botMember.roles.highest.position <= targetRole.position) {
      return {
        allowed: false,
        reason: `Role @${targetRole.name} (position ${targetRole.position}) is higher than or equal to bot's highest role (position ${botMember.roles.highest.position}).`,
      };
    }

    return { allowed: true };
  }

  static canBotManageMember(guild: Guild, targetMember: GuildMember): { allowed: boolean; reason?: string } {
    const botMember = guild.members.me;
    if (!botMember) return { allowed: false, reason: 'Bot member not found.' };

    if (guild.ownerId === targetMember.id) {
      return { allowed: false, reason: 'Bot cannot execute administrative operations against the Guild Owner.' };
    }

    if (botMember.roles.highest.position <= targetMember.roles.highest.position) {
      return {
        allowed: false,
        reason: `Target user ${targetMember.user.tag} has a role equal to or higher than the bot's highest role.`,
      };
    }

    return { allowed: true };
  }
}
