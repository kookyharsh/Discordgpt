import { z } from 'zod';

export enum IntentStatus {
  DIRECT_ACTION = 'direct_action',
  CLARIFICATION_REQUIRED = 'clarification_required',
  UNSUPPORTED = 'unsupported',
  CAPABILITY_UNAVAILABLE = 'capability_unavailable',
  PERMISSION_ANALYSIS_REQUIRED = 'permission_analysis_required',
  CONFIRMATION_REQUIRED = 'confirmation_required',
  ACTION_PLAN = 'action_plan',
  REJECTED = 'rejected',
}

export const ActionStepSchema = z.object({
  id: z.string(),
  action: z.string(),
  parameters: z.record(z.any()),
});

export const ParsedIntentSchema = z.object({
  status: z.nativeEnum(IntentStatus),
  action: z.string().optional(),
  parameters: z.record(z.any()).optional(),
  steps: z.array(ActionStepSchema).optional(),
  question: z.string().optional(),
  options: z.array(z.string()).optional(),
  reason: z.string().optional(),
});

export type ParsedIntent = z.infer<typeof ParsedIntentSchema>;

export interface LLMProvider {
  parseIntent(
    prompt: string,
    context: {
      guildId: string;
      channels: Array<{ id: string; name: string }>;
      roles: Array<{ id: string; name: string }>;
      allowedActions: string[];
    }
  ): Promise<ParsedIntent>;
}
