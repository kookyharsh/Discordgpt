import { describe, it, expect } from 'vitest';
import '../actions/channel-actions.js';
import '../actions/role-actions.js';
import '../actions/member-actions.js';
import '../actions/message-actions.js';
import { parseSettingValue, settingField } from './setting-options.js';

describe('parseSettingValue', () => {
  it('parses booleans loosely', () => {
    expect(parseSettingValue('enabled', 'true')).toEqual({ ok: true, value: true });
    expect(parseSettingValue('enabled', 'OFF')).toEqual({ ok: true, value: false });
    expect(parseSettingValue('enabled', 'maybe').ok).toBe(false);
  });

  it('validates IANA timezones', () => {
    expect(parseSettingValue('timezone', 'UTC')).toEqual({ ok: true, value: 'UTC' });
    expect(parseSettingValue('timezone', 'America/New_York').ok).toBe(true);
    expect(parseSettingValue('timezone', 'Mars/Olympus').ok).toBe(false);
    expect(parseSettingValue('timezone', '').ok).toBe(false);
  });

  it('validates action lists against the registry', () => {
    expect(parseSettingValue('allowed_actions', 'create_channel, ban_member')).toEqual({
      ok: true,
      value: ['create_channel', 'ban_member'],
    });
    expect(parseSettingValue('allowed_actions', '').value).toEqual([]);
    expect(parseSettingValue('disabled_actions', 'delete-channel').value).toEqual(['delete_channel']);
    const bad = parseSettingValue('allowed_actions', 'create_channel, nuke_server');
    expect(bad.ok).toBe(false);
    expect(bad.error).toContain('nuke_server');
  });

  it('rejects unknown keys', () => {
    expect(parseSettingValue('confirmation_mode', 'strict').ok).toBe(false);
  });

  it('maps keys to Prisma fields', () => {
    expect(settingField('enabled')).toBe('enabled');
    expect(settingField('timezone')).toBe('timezone');
    expect(settingField('allowed_actions')).toBe('allowedActions');
    expect(settingField('disabled_actions')).toBe('disabledActions');
    expect(settingField('nope')).toBeNull();
  });
});
