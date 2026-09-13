import { Queue, Worker, Job } from 'bullmq';
import Redis from 'ioredis';
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';
import { ScheduledJobData } from './types.js';
import { ScheduledActionRepository, GuildRepository } from '../database/repositories.js';
import { ActionDispatcher } from '../actions/dispatcher.js';
import { Client } from 'discord.js';

export class ActionScheduler {
  private queue: Queue;
  private worker?: Worker;
  private redisConnection: Redis;

  constructor() {
    this.redisConnection = new Redis(config.REDIS_URL, { maxRetriesPerRequest: null });
    this.queue = new Queue('discord-scheduled-actions', { connection: this.redisConnection as any });
  }

  async scheduleJob(data: ScheduledJobData, repeatOpts?: { pattern?: string; tz?: string }) {
    await this.queue.add(
      `job:${data.scheduledActionId}`,
      data,
      repeatOpts?.pattern
        ? { repeat: { pattern: repeatOpts.pattern, tz: repeatOpts.tz || 'UTC' } }
        : undefined
    );
  }

  async startWorker(discordClient: Client) {
    this.worker = new Worker(
      'discord-scheduled-actions',
      async (job: Job<ScheduledJobData>) => {
        logger.info({ jobId: job.id, guildId: job.data.guildId }, 'Executing scheduled job');

        const { guildId, createdByUserId, actionPlan, scheduledActionId } = job.data;

        const guild = await discordClient.guilds.fetch(guildId);
        if (!guild) {
          throw new Error(`Guild ${guildId} not found during scheduled job execution.`);
        }

        const actorMember = await guild.members.fetch(createdByUserId);
        if (!actorMember) {
          throw new Error(`User ${createdByUserId} not found in guild during scheduled execution.`);
        }

        const settings = await GuildRepository.getSettings(guildId);

        const ctx = {
          guildId,
          userId: createdByUserId,
          executionId: `sched-${job.id}-${Date.now()}`,
          guild,
          actorMember,
          settings,
        };

        if (actionPlan.type) {
          const dispatchRes = await ActionDispatcher.dispatch(actionPlan.type, actionPlan.input, ctx);
          if (!dispatchRes.success) {
            logger.error({ error: dispatchRes.error }, 'Scheduled job execution failed policy/permission check');
            throw new Error(`Scheduled action failed: ${dispatchRes.error}`);
          }
        }
      },
      { connection: this.redisConnection as any }
    );

    this.worker.on('failed', (job, err) => {
      logger.error({ jobId: job?.id, err }, 'Scheduled job failed');
    });
  }

  async reconcileSchedules(discordClient: Client) {
    logger.info('Reconciling active schedules from database...');
    const activeSchedules = await ScheduledActionRepository.listAllActive();

    for (const sched of activeSchedules) {
      await this.scheduleJob(
        {
          scheduledActionId: sched.id,
          guildId: sched.guildId,
          createdByUserId: sched.createdByUserId,
          actionPlan: sched.actionPlan,
          cronExpression: sched.cronExpression || undefined,
          timezone: sched.timezone,
        },
        sched.cronExpression ? { pattern: sched.cronExpression, tz: sched.timezone } : undefined
      );
    }
  }
}
