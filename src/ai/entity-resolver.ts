import { DiscordAdapter } from '../discord/types.js';

export interface ResolvedEntity {
  id: string;
  name: string;
  type: 'channel' | 'role' | 'member';
}

export class EntityResolver {
  constructor(private adapter: DiscordAdapter) {}

  async resolveChannel(guildId: string, query: string): Promise<{ match: ResolvedEntity | null; ambiguous: ResolvedEntity[] }> {
    const channels = await this.adapter.listChannels(guildId);
    const cleanQuery = query.replace(/^#/, '').toLowerCase().trim();

    const exact = channels.filter((c) => c.name.toLowerCase() === cleanQuery || c.id === cleanQuery);
    if (exact.length === 1) {
      return { match: { id: exact[0].id, name: exact[0].name, type: 'channel' }, ambiguous: [] };
    }

    const partial = channels.filter((c) => c.name.toLowerCase().includes(cleanQuery));
    if (partial.length === 1) {
      return { match: { id: partial[0].id, name: partial[0].name, type: 'channel' }, ambiguous: [] };
    }

    if (partial.length > 1) {
      return {
        match: null,
        ambiguous: partial.map((c) => ({ id: c.id, name: c.name, type: 'channel' })),
      };
    }

    return { match: null, ambiguous: [] };
  }

  async resolveRole(guildId: string, query: string): Promise<{ match: ResolvedEntity | null; ambiguous: ResolvedEntity[] }> {
    const roles = await this.adapter.listRoles(guildId);
    const cleanQuery = query.replace(/^@/, '').toLowerCase().trim();

    const exact = roles.filter((r) => r.name.toLowerCase() === cleanQuery || r.id === cleanQuery);
    if (exact.length === 1) {
      return { match: { id: exact[0].id, name: exact[0].name, type: 'role' }, ambiguous: [] };
    }

    const partial = roles.filter((r) => r.name.toLowerCase().includes(cleanQuery));
    if (partial.length === 1) {
      return { match: { id: partial[0].id, name: partial[0].name, type: 'role' }, ambiguous: [] };
    }

    if (partial.length > 1) {
      return {
        match: null,
        ambiguous: partial.map((r) => ({ id: r.id, name: r.name, type: 'role' })),
      };
    }

    return { match: null, ambiguous: [] };
  }

  async resolveMember(guildId: string, query: string): Promise<{ match: ResolvedEntity | null; ambiguous: ResolvedEntity[] }> {
    const cleanQuery = query.replace(/^@/, '').toLowerCase().trim();
    const member = await this.adapter.getMember(guildId, cleanQuery);
    if (member) {
      return { match: { id: member.id, name: member.displayName, type: 'member' }, ambiguous: [] };
    }
    return { match: null, ambiguous: [] };
  }
}
