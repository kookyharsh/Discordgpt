import { z } from 'zod';
import { Guild, GuildMember } from 'discord.js';

export enum RiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum ConfirmationPolicy {
  NOT_REQUIRED = 'NOT_REQUIRED',
  REQUIRED = 'REQUIRED',
  ALWAYS_CONFIRM = 'ALWAYS_CONFIRM',
}

export interface ExecutionContext {
  guildId: string;
  userId: string;
  executionId: string;
  guild: Guild;
  actorMember: GuildMember;
  settings?: any;
}

export interface ActionDefinition<TInput = any, TOutput = any> {
  type: string;
  description: string;
  inputSchema: z.ZodSchema<TInput>;
  requiredBotPermissions: bigint[];
  requiredUserPermissions: bigint[];
  riskLevel: RiskLevel;
  confirmationPolicy: ConfirmationPolicy;
  handler: (ctx: ExecutionContext, input: TInput) => Promise<TOutput>;
}
