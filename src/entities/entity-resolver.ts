import { Guild, GuildMember, Role, GuildBasedChannel } from 'discord.js';

export interface ResolutionResult<T> {
  resolved?: T;
  matches?: T[];
  ambiguous: boolean;
  notFound: boolean;
}

export class EntityResolver {
  static async resolveChannel(guild: Guild, query: string): Promise<ResolutionResult<GuildBasedChannel>> {
    const cleaned = query.replace(/^#/, '').trim().toLowerCase();
    const channels = await guild.channels.fetch();

    const matches: GuildBasedChannel[] = [];
    for (const [id, ch] of channels) {
      if (!ch) continue;
      if (ch.id === cleaned || ch.name.toLowerCase() === cleaned) {
        matches.push(ch);
      }
    }

    if (matches.length === 1) {
      return { resolved: matches[0], ambiguous: false, notFound: false };
    } else if (matches.length > 1) {
      return { matches, ambiguous: true, notFound: false };
    }

    const partialMatches: GuildBasedChannel[] = [];
    for (const [id, ch] of channels) {
      if (!ch) continue;
      if (ch.name.toLowerCase().includes(cleaned)) {
        partialMatches.push(ch);
      }
    }

    if (partialMatches.length === 1) {
      return { resolved: partialMatches[0], ambiguous: false, notFound: false };
    } else if (partialMatches.length > 1) {
      return { matches: partialMatches, ambiguous: true, notFound: false };
    }

    return { ambiguous: false, notFound: true };
  }

  static async resolveRole(guild: Guild, query: string): Promise<ResolutionResult<Role>> {
    const cleaned = query.replace(/^@/, '').trim().toLowerCase();
    const roles = await guild.roles.fetch();

    const matches: Role[] = [];
    for (const [id, role] of roles) {
      if (role.id === cleaned || role.name.toLowerCase() === cleaned) {
        matches.push(role);
      }
    }

    if (matches.length === 1) {
      return { resolved: matches[0], ambiguous: false, notFound: false };
    } else if (matches.length > 1) {
      return { matches, ambiguous: true, notFound: false };
    }

    const partialMatches: Role[] = [];
    for (const [id, role] of roles) {
      if (role.name.toLowerCase().includes(cleaned)) {
        partialMatches.push(role);
      }
    }

    if (partialMatches.length === 1) {
      return { resolved: partialMatches[0], ambiguous: false, notFound: false };
    } else if (partialMatches.length > 1) {
      return { matches: partialMatches, ambiguous: true, notFound: false };
    }

    return { ambiguous: false, notFound: true };
  }

  static async resolveMember(guild: Guild, query: string): Promise<ResolutionResult<GuildMember>> {
    // ID or mention lookup via single REST fetch. A full guild.members.fetch()
    // requires the privileged Server Members intent and is too slow for the
    // 3s interaction window, so username search is intentionally unsupported.
    const mentionMatch = query.match(/^<@!?(\d+)>$/);
    const candidate = (mentionMatch ? mentionMatch[1] : query.replace(/^@/, '').trim()).trim();
    if (/^\d{15,25}$/.test(candidate)) {
      try {
        const member = await guild.members.fetch(candidate);
        if (member) return { resolved: member, ambiguous: false, notFound: false };
      } catch {
        // fall through to notFound
      }
    }

    return { ambiguous: false, notFound: true };
  }
}
