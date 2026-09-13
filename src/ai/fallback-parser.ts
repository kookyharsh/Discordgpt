import { ParsedIntent, IntentStatus } from './types.js';

export class FallbackParser {
  static parse(prompt: string): ParsedIntent | null {
    const normalized = prompt.trim().toLowerCase();
    const raw = prompt.trim();

    const createChannelMatch = normalized.match(/create (?:a )?(?:text )?channel (?:called |named )?([a-z0-9-_]+)/i);
    if (createChannelMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'create_channel',
        parameters: {
          name: createChannelMatch[1],
          type: 'text',
        },
      };
    }

    const deleteChannelMatch = normalized.match(/(?:delete|remove) (?:the )?(?:text )?channel (?:called |named )?#?([a-z0-9-_]+)/i);
    if (deleteChannelMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'delete_channel',
        parameters: { channelName: deleteChannelMatch[1] },
      };
    }

    const createRoleMatch = normalized.match(/create (?:a )?role (?:called |named )?([a-z0-9-_ ]+?)\s*$/i);
    if (createRoleMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'create_role',
        parameters: { name: createRoleMatch[1].trim() },
      };
    }

    // Mention-based moderation (IDs survive without privileged intents).
    // NOTE: untimeout/unban checks must precede timeout/ban ("untimeout" contains "timeout").
    const untimeoutMatch = raw.match(/\b(?:untimeout|unmute)\s+<@!?(\d{15,25})>/i);
    if (untimeoutMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'untimeout_member',
        parameters: { memberId: untimeoutMatch[1] },
      };
    }

    const timeoutMatch = raw.match(/(?<!un)\btimeout\s+<@!?(\d{15,25})>(?:\s+for\s+(\d+)\s*(s(?:ec(?:ond)?s?)?|m(?:in(?:ute)?s?)?)?)?/i);
    if (timeoutMatch) {
      const amount = timeoutMatch[2] ? parseInt(timeoutMatch[2], 10) : 300;
      const unit = (timeoutMatch[3] || 's').toLowerCase();
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'timeout_member',
        parameters: {
          memberId: timeoutMatch[1],
          durationSeconds: unit.startsWith('m') ? amount * 60 : amount,
        },
      };
    }

    const banMatch = raw.match(/(?<!un)\bban\s+<@!?(\d{15,25})>(?:\s+(?:for\s+)?(.+))?/i);
    if (banMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'ban_member',
        parameters: {
          memberId: banMatch[1],
          ...(banMatch[2] ? { reason: banMatch[2].trim().slice(0, 512) } : {}),
        },
      };
    }

    const assignMatch = raw.match(/<@!?(\d{15,25})>[\s\S]*?<@&(\d{15,25})>|<@&(\d{15,25})>[\s\S]*?<@!?(\d{15,25})>/);
    if (assignMatch) {
      const memberId = assignMatch[1] ?? assignMatch[4];
      const roleId = assignMatch[2] ?? assignMatch[3];
      if (memberId && roleId) {
        return {
          status: IntentStatus.DIRECT_ACTION,
          action: 'assign_role',
          parameters: { memberId, roleId },
        };
      }
    }

    const kickMatch = raw.match(/\bkick\s+<@!?(\d{15,25})>(?:\s+(?:for\s+)?(.+))?/i);
    if (kickMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'kick_member',
        parameters: {
          memberId: kickMatch[1],
          ...(kickMatch[2] ? { reason: kickMatch[2].trim().slice(0, 512) } : {}),
        },
      };
    }

    const unbanMatch = normalized.match(/\bunban\s+(?:<@!?(\d{15,25})>|(\d{15,25}))/);
    if (unbanMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'unban_member',
        parameters: { userId: unbanMatch[1] ?? unbanMatch[2] },
      };
    }

    const nickMatch = raw.match(/\bnick(?:name)?\s+<@!?(\d{15,25})>\s+(.+?)\s*$/i);
    if (nickMatch) {
      const name = nickMatch[2].trim();
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'set_nickname',
        parameters: {
          memberId: nickMatch[1],
          ...(/^(clear|reset|remove)$/i.test(name) ? {} : { nickname: name.slice(0, 32) }),
        },
      };
    }

    const slowMatch = normalized.match(/\bslow ?mode\s+(off|disable|0|\d+)\b/i);
    if (slowMatch) {
      const seconds = /^\d+$/.test(slowMatch[1]) ? Math.min(parseInt(slowMatch[1], 10), 21600) : 0;
      const chan = normalized.match(/(?:in|for)\s+#?([a-z0-9-_]+)/);
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'set_slowmode',
        parameters: {
          seconds,
          ...(chan ? { channelName: chan[1] } : {}),
        },
      };
    }

    const unlockMatch = normalized.match(/\bunlock\b(?:\s+channel)?\s*#?([a-z0-9-_]+)?/);
    if (unlockMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'unlock_channel',
        parameters: { ...(unlockMatch[1] ? { channelName: unlockMatch[1] } : {}) },
      };
    }

    const lockMatch = normalized.match(/\block\b(?:\s+channel)?\s*#?([a-z0-9-_]+)?/);
    if (lockMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'lock_channel',
        parameters: { ...(lockMatch[1] ? { channelName: lockMatch[1] } : {}) },
      };
    }

    const renameMatch = normalized.match(/\brename\s+(?:channel\s+)?#?([a-z0-9-_]+)\s+to\s+([a-z0-9-_ ]+?)\s*$/i);
    if (renameMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'rename_channel',
        parameters: { channelName: renameMatch[1], newName: renameMatch[2].trim() },
      };
    }

    const purgeMatch = normalized.match(/\b(purge|clear|delete)\s+(\d{1,3})(?:\s+messages?)?(?:\s+(?:in|from)\s+#?([a-z0-9-_]+))?/);
    if (purgeMatch) {
      const verb = purgeMatch[1];
      const hasTarget = /messages?/.test(normalized) || !!purgeMatch[3];
      // Bare "delete 5" is ambiguous (channel? role?) - leave it to the LLM.
      if (verb !== 'delete' || hasTarget) {
        return {
          status: IntentStatus.DIRECT_ACTION,
          action: 'purge_messages',
          parameters: {
            limit: Math.min(parseInt(purgeMatch[2], 10), 100),
            ...(purgeMatch[3] ? { channelName: purgeMatch[3] } : {}),
          },
        };
      }
    }

    const sendMessageMatch = normalized.match(/send (?:message )?"([^"]+)" to <#?([a-z0-9-_]+)>?/i);
    if (sendMessageMatch) {
      return {
        status: IntentStatus.DIRECT_ACTION,
        action: 'send_message',
        parameters: {
          content: sendMessageMatch[1],
          channelName: sendMessageMatch[2],
        },
      };
    }

    return null;
  }
}
