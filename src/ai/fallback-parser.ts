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
    const timeoutMatch = raw.match(/timeout\s+<@!?(\d{15,25})>(?:\s+for\s+(\d+)\s*(s(?:ec(?:ond)?s?)?|m(?:in(?:ute)?s?)?)?)?/i);
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

    const banMatch = raw.match(/ban\s+<@!?(\d{15,25})>(?:\s+(?:for\s+)?(.+))?/i);
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
