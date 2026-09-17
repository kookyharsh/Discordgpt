import { describe, it, expect } from 'vitest';
import { ActionRegistry } from './registry.js';
import './channel-actions.js';
import './role-actions.js';
import './member-actions.js';
import './message-actions.js';

describe('Action Whitelist Registry Tests', () => {
  it('registers supported actions', () => {
    expect(ActionRegistry.isRegistered('create_channel')).toBe(true);
    expect(ActionRegistry.isRegistered('delete_channel')).toBe(true);
    expect(ActionRegistry.isRegistered('assign_role')).toBe(true);
    expect(ActionRegistry.isRegistered('timeout_member')).toBe(true);
  });

  it('rejects unregistered unknown actions', () => {
    expect(ActionRegistry.isRegistered('arbitrary_code_exec')).toBe(false);
    expect(ActionRegistry.get('unknown_action')).toBeUndefined();
  });
});
