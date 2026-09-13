export interface ScheduledJobData {
  scheduledActionId: string;
  guildId: string;
  createdByUserId: string;
  actionPlan: any;
  cronExpression?: string;
  timezone?: string;
}
