import { ParsedIntent, IntentStatus } from './types.js';

export class FallbackParser {
  static parse(prompt: string): ParsedIntent | null {
    const normalized = prompt.trim().toLowerCase();

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

    const sendMessageMatch = normalized.match(/send (?:message )?"([^"]+)" to ([a-z0-9-_]+)/i);
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
