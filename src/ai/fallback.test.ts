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

  it('parses moderation fallbacks', () => {
    expect(FallbackParser.parse('Kick <@123456789012345678>')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'kick_member',
    });
    expect(FallbackParser.parse('Unban 123456789012345678')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'unban_member',
      parameters: { userId: '123456789012345678' },
    });
    expect(FallbackParser.parse('Untimeout <@123456789012345678>')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'untimeout_member',
    });
    // "unban @mention" must not parse as a ban.
    expect(FallbackParser.parse('Unban <@123456789012345678>')!.action).toBe('unban_member');
  });

  it('parses channel moderation fallbacks', () => {
    expect(FallbackParser.parse('Slowmode 10 in general')).toMatchObject({
      status: IntentStatus.DIRECT_ACTION,
      action: 'set_slowmode',
      parameters: { seconds: 10, channelName: 'general' },
    });
    expect(FallbackParser.parse('Slowmode off')).toMatchObject({
      action: 'set_slowmode',
      parameters: { seconds: 0 },
    });
    expect(FallbackParser.parse('Lock announcements')).toMatchObject({ action: 'lock_channel' });
    expect(FallbackParser.parse('Unlock')).toMatchObject({ action: 'unlock_channel' });
    expect(FallbackParser.parse('Rename general to lobby')).toMatchObject({
      action: 'rename_channel',
      parameters: { channelName: 'general', newName: 'lobby' },
    });
    expect(FallbackParser.parse('Purge 20 in general')).toMatchObject({
      action: 'purge_messages',
      parameters: { limit: 20, channelName: 'general' },
    });
    // Bare "delete 5" is ambiguous - leave it to the LLM.
    expect(FallbackParser.parse('Delete 5')).toBeNull();
  });

  it('parses nickname fallback', () => {
    expect(FallbackParser.parse('Nick <@123456789012345678> Helper')).toMatchObject({
      action: 'set_nickname',
      parameters: { memberId: '123456789012345678', nickname: 'Helper' },
    });
  });
});
