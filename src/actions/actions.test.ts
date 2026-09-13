import { describe, it, expect } from 'vitest';
import { ActionRegistry } from './registry.js';
import './channel-actions.js';
import './role-actions.js';
import './member-actions.js';
import './message-actions.js';

describe('Action Whitelist Registry Tests', () => {
  it('registers supported actions', () => {
    for (const name of [
      'create_channel',
      'delete_channel',
      'set_slowmode',
      'lock_channel',
      'unlock_channel',
      'rename_channel',
      'set_topic',
      'create_role',
      'assign_role',
      'remove_role',
      'edit_role',
      'delete_role',
      'timeout_member',
      'untimeout_member',
      'kick_member',
      'ban_member',
      'unban_member',
      'set_nickname',
      'move_member',
      'send_message',
      'pin_message',
      'unpin_message',
      'purge_messages',
    ]) {
      expect(ActionRegistry.isRegistered(name), name).toBe(true);
    }
  });

  it('rejects unregistered unknown actions', () => {
    expect(ActionRegistry.isRegistered('arbitrary_code_exec')).toBe(false);
    expect(ActionRegistry.get('unknown_action')).toBeUndefined();
  });

  it('gives every action a help-ready description', () => {
    for (const action of ActionRegistry.getAll()) {
      expect(action.description?.trim().length, action.type).toBeGreaterThan(0);
    }
  });
});
