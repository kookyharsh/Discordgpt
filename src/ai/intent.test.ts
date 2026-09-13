import { describe, it, expect } from 'vitest';
import { ParsedIntentSchema, IntentStatus } from './types.js';
import { historyBlock } from './conversation-context.js';

describe('chat intent', () => {
  it('accepts chat status with a message', () => {
    const parsed = ParsedIntentSchema.parse({
      status: 'chat',
      message: 'Here is what I know about your server…',
    });
    expect(parsed.status).toBe(IntentStatus.CHAT);
    expect(parsed.message).toContain('your server');
  });

  it('still accepts direct_action without a message', () => {
    const parsed = ParsedIntentSchema.parse({
      status: 'direct_action',
      action: 'create_channel',
      parameters: { name: 'welcome' },
    });
    expect(parsed.message).toBeUndefined();
  });

  it('formats history for prompts', () => {
    expect(historyBlock([])).toContain('(none)');
    expect(historyBlock(undefined)).toContain('(none)');
    expect(historyBlock(['user: hi', 'assistant: hello'])).toContain('user: hi');
  });
});
