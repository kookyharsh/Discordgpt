import { prisma } from './prisma.js';
import { Prisma } from '@prisma/client';

export class GuildRepository {
  static async findOrCreate(discordGuildId: string, name?: string) {
    // Upsert: two concurrent /prompt commands otherwise race findUnique+create (P2002).
    const guild = await prisma.guild.upsert({
      where: { discordGuildId },
      update: name ? { name } : {},
      create: {
        discordGuildId,
        name,
        settings: {
          create: {
            timezone: 'UTC',
            enabled: true,
          },
        },
      },
      include: { settings: true },
    });

    // Backfill settings for guilds created before the nested-create (or partial writes).
    if (!guild.settings) {
      await prisma.guildSettings.create({
        data: { guildId: discordGuildId, timezone: 'UTC', enabled: true },
      });
      return prisma.guild.findUniqueOrThrow({
        where: { discordGuildId },
        include: { settings: true },
      });
    }

    return guild;
  }

  static async getSettings(guildId: string) {
    return prisma.guildSettings.findUnique({
      where: { guildId },
    });
  }

  static async updateSettings(guildId: string, data: Prisma.GuildSettingsUpdateInput) {
    return prisma.guildSettings.update({
      where: { guildId },
      data,
    });
  }
}

export class ExecutionRepository {
  static async createExecution(data: {
    guildId: string;
    userId: string;
    prompt: string;
    status: string;
    parsedIntent?: any;
    actionPlan?: any;
  }) {
    return prisma.actionExecution.create({
      data: {
        guildId: data.guildId,
        userId: data.userId,
        prompt: data.prompt,
        status: data.status,
        parsedIntent: data.parsedIntent ? (data.parsedIntent as Prisma.InputJsonValue) : Prisma.DbNull,
        actionPlan: data.actionPlan ? (data.actionPlan as Prisma.InputJsonValue) : Prisma.DbNull,
      },
    });
  }

  static async updateExecutionStatus(
    id: string,
    guildId: string,
    status: string,
    error?: string,
    completedAt?: Date
  ) {
    return prisma.actionExecution.updateMany({
      where: { id, guildId },
      data: {
        status,
        error,
        completedAt: completedAt || (status === 'COMPLETED' || status === 'FAILED' ? new Date() : undefined),
      },
    });
  }
}

export class AuditRepository {
  static async log(data: {
    guildId: string;
    userId: string;
    executionId?: string;
    action: string;
    targetType?: string;
    targetId?: string;
    parameters?: any;
    result?: any;
    status: 'SUCCESS' | 'FAILURE';
    error?: string;
  }) {
    return prisma.auditLog.create({
      data: {
        guildId: data.guildId,
        userId: data.userId,
        executionId: data.executionId,
        action: data.action,
        targetType: data.targetType,
        targetId: data.targetId,
        parameters: data.parameters ? (data.parameters as Prisma.InputJsonValue) : Prisma.DbNull,
        result: data.result ? (data.result as Prisma.InputJsonValue) : Prisma.DbNull,
        status: data.status,
        error: data.error,
      },
    });
  }

  static async getRecentLogs(guildId: string, limit = 20) {
    return prisma.auditLog.findMany({
      where: { guildId },
      orderBy: { createdAt: 'desc' },
      take: limit,
    });
  }
}

export class ConfirmationRepository {
  static async create(data: {
    guildId: string;
    userId: string;
    planHash: string;
    actionNonce: string;
    actionPlan: any;
    expiresInMs?: number;
  }) {
    const expiresAt = new Date(Date.now() + (data.expiresInMs || 5 * 60 * 1000));
    return prisma.confirmationRequest.create({
      data: {
        guildId: data.guildId,
        userId: data.userId,
        planHash: data.planHash,
        actionNonce: data.actionNonce,
        actionPlan: data.actionPlan as Prisma.InputJsonValue,
        expiresAt,
      },
    });
  }

  static async findAndConsume(nonce: string, guildId: string, userId: string, expectedHash: string) {
    const confirmation = await prisma.confirmationRequest.findFirst({
      where: {
        actionNonce: nonce,
        guildId,
        userId,
        consumed: false,
        expiresAt: { gt: new Date() },
      },
    });

    if (!confirmation) return null;

    if (expectedHash && confirmation.planHash !== expectedHash) {
      return null;
    }

    await prisma.confirmationRequest.update({
      where: { id: confirmation.id },
      data: { consumed: true },
    });

    return confirmation;
  }
}

export class ScheduledActionRepository {
  static async create(data: {
    guildId: string;
    createdByUserId: string;
    actionPlan: any;
    scheduleType: 'CRON' | 'ONE_TIME';
    cronExpression?: string;
    executeAt?: Date;
    timezone?: string;
    nextRunAt?: Date;
  }) {
    return prisma.scheduledAction.create({
      data: {
        guildId: data.guildId,
        createdByUserId: data.createdByUserId,
        actionPlan: data.actionPlan as Prisma.InputJsonValue,
        scheduleType: data.scheduleType,
        cronExpression: data.cronExpression,
        executeAt: data.executeAt,
        timezone: data.timezone || 'UTC',
        nextRunAt: data.nextRunAt,
      },
    });
  }

  static async listActiveForGuild(guildId: string) {
    return prisma.scheduledAction.findMany({
      where: { guildId, enabled: true },
    });
  }

  static async listAllActive() {
    return prisma.scheduledAction.findMany({
      where: { enabled: true },
    });
  }

  static async delete(id: string, guildId: string) {
    return prisma.scheduledAction.deleteMany({
      where: { id, guildId },
    });
  }
}
