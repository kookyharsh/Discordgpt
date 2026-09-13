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
  CHAT = 'chat',
}

export const ActionStepSchema = z.object({
  id: z.string(),
  action: z.string(),
  parameters: z.record(z.any()),
});

export type ActionStep = z.infer<typeof ActionStepSchema>;

export const ParsedIntentSchema = z.object({
  status: z.nativeEnum(IntentStatus),
  action: z.string().optional(),
  parameters: z.record(z.any()).optional(),
  steps: z.array(ActionStepSchema).optional(),
  question: z.string().optional(),
  options: z.array(z.string()).optional(),
  reason: z.string().optional(),
  message: z.string().optional(),
});

export type ParsedIntent = z.infer<typeof ParsedIntentSchema>;

export interface LLMContext {
  guildId: string;
  channels: Array<{ id: string; name: string }>;
  roles: Array<{ id: string; name: string }>;
  allowedActions: string[];
  /** Oldest-first "role: text" lines, already truncated. */
  history?: string[];
}

export interface LLMProvider {
  parseIntent(prompt: string, context: LLMContext): Promise<ParsedIntent>;
  /** Free-chat reply. History is oldest-first "role: text" lines. */
  chat?(prompt: string, context: LLMContext): Promise<string>;
}
