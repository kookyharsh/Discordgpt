import { DiscordAdapter } from '../discord/types.js';
import { ActionRegistry } from '../actions/registry.js';

export interface PermissionCheckResult {
  allowed: boolean;
  reason?: string;
  missingBotPermissions?: string[];
  missingUserPermissions?: string[];
  hierarchyViolation?: boolean;
}

export class PermissionEngine {
  constructor(private adapter: DiscordAdapter) {}

  async checkActionPermissions(
    guildId: string,
    actorUserId: string,
    actionType: string,
    targetInfo?: { roleId?: string; targetUserId?: string; channelId?: string }
  ): Promise<PermissionCheckResult> {
    const actionDef = ActionRegistry.get(actionType);
    if (!actionDef) {
      return { allowed: false, reason: `Unknown action type: ${actionType}` };
    }

    // 1. Check Bot Permissions
    if (actionDef.requiredBotPermissions.length > 0) {
      const botCheck = await this.adapter.checkBotPermissions(guildId, actionDef.requiredBotPermissions);
      if (!botCheck.hasPermissions) {
        return {
          allowed: false,
          reason: `Bot is missing required Discord permission(s): ${botCheck.missing.join(', ')}`,
          missingBotPermissions: botCheck.missing,
        };
      }
    }

    // 2. Check User Permissions
    if (actionDef.requiredUserPermissions.length > 0) {
      const userCheck = await this.adapter.checkUserPermissions(
        guildId,
        actorUserId,
        actionDef.requiredUserPermissions,
        targetInfo?.channelId
      );
      if (!userCheck.hasPermissions) {
        return {
          allowed: false,
          reason: `Requesting user is missing required Discord permission(s): ${userCheck.missing.join(', ')}`,
          missingUserPermissions: userCheck.missing,
        };
      }
    }

    // 3. Check Role Hierarchy if targeting a role
    if (targetInfo?.roleId) {
      const userCanManageRole = await this.adapter.checkRoleHierarchy(guildId, actorUserId, targetInfo.roleId);
      if (!userCanManageRole) {
        return {
          allowed: false,
          reason: `The requested target role is higher than or equal to your highest role in the server hierarchy.`,
          hierarchyViolation: true,
        };
      }

      const botCanManageRole = await this.adapter.checkBotRoleHierarchy(guildId, targetInfo.roleId);
      if (!botCanManageRole) {
        return {
          allowed: false,
          reason: `The target role is higher than or equal to the bot's highest role. Please move the bot role higher than the target role.`,
          hierarchyViolation: true,
        };
      }
    }

    // 4. Check Member Hierarchy if targeting a member
    if (targetInfo?.targetUserId) {
      const userCanManageMember = await this.adapter.checkMemberHierarchy(guildId, actorUserId, targetInfo.targetUserId);
      if (!userCanManageMember) {
        return {
          allowed: false,
          reason: `You cannot perform this action on a member with a higher or equal role hierarchy than yourself.`,
          hierarchyViolation: true,
        };
      }

      const botCanManageMember = await this.adapter.checkBotMemberHierarchy(guildId, targetInfo.targetUserId);
      if (!botCanManageMember) {
        return {
          allowed: false,
          reason: `The bot cannot perform this action on a member with a higher or equal role hierarchy than the bot.`,
          hierarchyViolation: true,
        };
      }
    }

    return { allowed: true };
  }
}
