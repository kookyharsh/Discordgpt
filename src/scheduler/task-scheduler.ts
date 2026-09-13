import cronParser from 'cron-parser';
import { ActionDispatcher, DispatchPlan } from '../actions/dispatcher.js';
import { ExecutionContext } from '../actions/types.js';
import { logger } from '../utils/logger.js';

export interface ScheduledJobData {
  scheduleId: string;
  guildId: string;
  userId: string;
  plan: DispatchPlan;
  cronExpression: string;
  timezone: string;
}

export class TaskScheduler {
  private activeJobs: Map<string, ScheduledJobData> = new Map();

  constructor(private dispatcher: ActionDispatcher) {}

  public validateCron(cronExpression: string): boolean {
    try {
      const parse = (cronParser as any).parseExpression || (cronParser as any).default?.parseExpression;
      if (typeof parse === 'function') {
        parse(cronExpression);
        return true;
      }
      return true;
    } catch {
      return false;
    }
  }

  public registerSchedule(data: ScheduledJobData): void {
    if (!this.validateCron(data.cronExpression)) {
      throw new Error(`InvalidCronExpressionError: '${data.cronExpression}' is not a valid cron expression.`);
    }
    this.activeJobs.set(data.scheduleId, data);
    logger.info(`Registered schedule ${data.scheduleId} for guild ${data.guildId}`);
  }

  public async executeScheduledTask(scheduleId: string, ctx: ExecutionContext): Promise<void> {
    const jobData = this.activeJobs.get(scheduleId);
    if (!jobData) {
      throw new Error(`Schedule ${scheduleId} not found.`);
    }

    if (jobData.guildId !== ctx.guildId) {
      throw new Error(`Tenant mismatch on schedule execution.`);
    }

    logger.info(`Executing scheduled task ${scheduleId}`);
    await this.dispatcher.dispatch(jobData.plan, ctx);
  }

  public removeSchedule(scheduleId: string): void {
    this.activeJobs.delete(scheduleId);
  }

  public listSchedules(guildId: string): ScheduledJobData[] {
    return Array.from(this.activeJobs.values()).filter((j) => j.guildId === guildId);
  }
}
