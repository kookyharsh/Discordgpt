import { z } from 'zod';
import { DiscordAdapter } from '../discord/types.js';
import { logger } from '../utils/logger.js';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ConfirmationPolicy = 'NOT_REQUIRED' | 'REQUIRED';

export interface ExecutionContext {
  guildId: string;
  userId: string;
  interactionId?: string;
  executionId: string;
  logger: typeof logger;
  discordAdapter: DiscordAdapter;
  createdResources?: Array<{ type: string; id: string }>;
}

export interface ActionDefinition<TInput = any, TOutput = any> {
  type: string;
  description: string;
  inputSchema: z.ZodSchema<TInput>;
  requiredBotPermissions: string[];
  requiredUserPermissions: string[];
  requiredIntents?: string[];
  riskLevel: RiskLevel;
  confirmationPolicy: ConfirmationPolicy;
  capabilityRequirements?: string[];
  targetRequirements?: string[];
  handler: (ctx: ExecutionContext, input: TInput) => Promise<TOutput>;
  rollback?: (ctx: ExecutionContext, resourceId: string) => Promise<void>;
}
