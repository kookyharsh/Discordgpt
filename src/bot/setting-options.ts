import { ActionRegistry } from '../actions/registry.js';

export const SETTING_KEYS = ['enabled', 'timezone', 'allowed_actions', 'disabled_actions'] as const;
export type SettingKey = (typeof SETTING_KEYS)[number];

export interface SettingParseResult {
  ok: boolean;
  value?: boolean | string | string[];
  error?: string;
}

/** Pure parser/validator for /prompt-settings values. Unit-tested. */
export function parseSettingValue(key: string, raw: string): SettingParseResult {
  const normalizedKey = key.trim().toLowerCase();
  const input = raw.trim();

  switch (normalizedKey) {
    case 'enabled': {
      const v = input.toLowerCase();
      if (['true', 'on', '1', 'yes'].includes(v)) return { ok: true, value: true };
      if (['false', 'off', '0', 'no'].includes(v)) return { ok: true, value: false };
      return { ok: false, error: `enabled must be true or false, got "${raw}".` };
    }
    case 'timezone': {
      if (!input) return { ok: false, error: 'timezone must not be empty (e.g. UTC, America/New_York).' };
      try {
        Intl.DateTimeFormat(undefined, { timeZone: input });
      } catch {
        return { ok: false, error: `"${raw}" is not a valid IANA timezone (e.g. UTC, America/New_York).` };
      }
      return { ok: true, value: input };
    }
    case 'allowed_actions':
    case 'disabled_actions': {
      if (input === '') return { ok: true, value: [] };
      const names = input
        .split(',')
        .map((s) => s.trim().toLowerCase().replace(/-/g, '_'))
        .filter(Boolean);
      const unknown = names.filter((n) => !ActionRegistry.isRegistered(n));
      if (unknown.length > 0) {
        return { ok: false, error: `Unknown action(s): ${unknown.join(', ')}. See /prompt-help for the catalog.` };
      }
      return { ok: true, value: [...new Set(names)] };
    }
    default:
      return { ok: false, error: `Unknown setting "${key}". Valid keys: ${SETTING_KEYS.join(', ')}.` };
  }
}

/** Maps a validated setting key to its Prisma GuildSettings field. */
export function settingField(key: string): 'enabled' | 'timezone' | 'allowedActions' | 'disabledActions' | null {
  switch (key.trim().toLowerCase()) {
    case 'enabled':
      return 'enabled';
    case 'timezone':
      return 'timezone';
    case 'allowed_actions':
      return 'allowedActions';
    case 'disabled_actions':
      return 'disabledActions';
    default:
      return null;
  }
}
