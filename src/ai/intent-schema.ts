import { z } from 'zod';

export const ActionStepSchema = z.object({
  id: z.string(),
  action: z.string(),
  parameters: z.record(z.any()),
});

export const ParsedIntentSchema = z.discriminatedUnion('status', [
  z.object({
    status: z.literal('direct_action'),
    intentType: z.literal('single_action'),
    action: z.string(),
    parameters: z.record(z.any()),
  }),
  z.object({
    status: z.literal('action_plan'),
    intentType: z.literal('action_plan'),
    steps: z.array(ActionStepSchema),
  }),
  z.object({
    status: z.literal('clarification_required'),
    question: z.string(),
    missingFields: z.array(z.string()).optional(),
  }),
  z.object({
    status: z.literal('unsupported'),
    reason: z.string(),
  }),
  z.object({
    status: z.literal('capability_unavailable'),
    reason: z.string(),
  }),
  z.object({
    status: z.literal('rejected'),
    reason: z.string(),
  }),
]);

export type ParsedIntent = z.infer<typeof ParsedIntentSchema>;
