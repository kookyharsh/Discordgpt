import { logger } from '../utils/logger.js';

export interface AuditLogEntry {
  id: string;
  guildId: string;
  userId: string;
  executionId?: string;
  action: string;
  targetType?: string;
  targetId?: string;
  parameters?: any;
  result?: any;
  status: 'SUCCESS' | 'FAILED' | 'PARTIAL_FAILURE';
  error?: string;
  createdAt: Date;
}

export class AuditLogger {
  private static inMemoryLogs: AuditLogEntry[] = [];

  public static async log(entry: Omit<AuditLogEntry, 'id' | 'createdAt'>): Promise<AuditLogEntry> {
    const fullEntry: AuditLogEntry = {
      ...entry,
      id: `audit-${Date.now()}-${Math.floor(Math.random() * 10000)}`,
      createdAt: new Date(),
    };

    // Sanitize parameters to ensure no secrets/tokens are logged
    if (fullEntry.parameters) {
      delete fullEntry.parameters.token;
      delete fullEntry.parameters.secret;
      delete fullEntry.parameters.password;
    }

    this.inMemoryLogs.push(fullEntry);
    logger.info({ audit: fullEntry }, `AuditLog: Guild ${fullEntry.guildId} User ${fullEntry.userId} Action ${fullEntry.action} -> ${fullEntry.status}`);
    return fullEntry;
  }

  public static getLogsForGuild(guildId: string, limit: number = 50): AuditLogEntry[] {
    return this.inMemoryLogs
      .filter((l) => l.guildId === guildId)
      .slice(-limit)
      .reverse();
  }
}
