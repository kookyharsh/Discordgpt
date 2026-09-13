import { describe, it, expect } from 'vitest';
import { FallbackParser } from './fallback-parser.js';
import { IntentStatus } from './types.js';

describe('FallbackParser offline coverage', () => {
  it('parses channel create/delete without LLM', () => {
    expect(FallbackParser.parse('Create channel welcome')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'create_channel',
    });
    expect(FallbackParser.parse('Delete channel old-chat')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'delete_channel',
    });
  });

  it('parses role creation', () => {
    expect(FallbackParser.parse('Create role Moderators')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'create_role',
    });
  });

  it('parses mention-based moderation', () => {
    expect(FallbackParser.parse('Timeout <@123456789012345678> for 300')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'timeout_member',
      parameters: { memberId: '123456789012345678', durationSeconds: 300 },
    });
    expect(FallbackParser.parse('Ban <@123456789012345678>')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'ban_member',
    });
  });

  it('parses mention-based role assignment', () => {
    expect(
      FallbackParser.parse('Give <@123456789012345678> the role <@&876543210987654321>')
    ).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'assign_role',
      parameters: { memberId: '123456789012345678', roleId: '876543210987654321' },
    });
  });

  it('returns null for genuinely ambiguous prompts', () => {
    expect(FallbackParser.parse('Do something nice for the community event next week')).toBeNull();
  });
});
