import { ActionDispatcher } from './dispatcher.js';
import { ConfirmationRepository } from '../database/repositories.js';
import { PlanHasher } from '../security/plan-hasher.js';
import { EntityResolver } from '../entities/entity-resolver.js';
import type { ExecutionContext } from './types.js';
import type { ActionStep } from '../ai/types.js';

export const MAX_PLAN_STEPS = 5;
export const PLAN_TYPE = '__plan__';

export interface PlanStepResult {
  stepId: string;
  action: string;
  ok: boolean;
  result?: any;
  error?: string;
}

export interface PlanConfirmation {
  nonce: string;
  actionType: string;
  riskLevel: string;
  stepLabel: string;
}

export interface PlanExecution {
  /** False when paused for a confirmation; call again after approval. */
  completed: boolean;
  results: PlanStepResult[];
  confirmation?: PlanConfirmation;
}

/** Human-readable plan outcome for embeds. Pure - unit-tested. */
export function summarizePlan(results: PlanStepResult[]): string {
  if (results.length === 0) return 'No steps were executed.';
  const ok = results.filter((r) => r.ok).length;
  const lines = results.map((r) =>
    r.ok ? `✓ ${r.action}` : `✗ ${r.action}: ${(r.error ?? 'failed').slice(0, 120)}`
  );
  return `${ok}/${results.length} steps succeeded.\n${lines.join('\n')}`.slice(0, 1800);
}

/**
 * Executes plan steps in order with the full safety pipeline per step.
 * Name-based params (channelName/roleName) resolve per step like single actions.
 * On a confirmation gate, the REMAINDER (current step onwards) is stashed under
 * a plan confirmation nonce; resume with executeActionPlan(steps, index, ctx).
 * Note: the dispatcher rows its own single-step confirmation first, which then
 * orphans (5-min expiry, harmless) - accepted to avoid duplicating gate policy.
 */
export async function executeActionPlan(
  steps: ActionStep[],
  startIndex: number,
  ctx: ExecutionContext
): Promise<PlanExecution> {
  const results: PlanStepResult[] = [];

  for (let i = startIndex; i < steps.length; i++) {
    const step = steps[i];
    const params: Record<string, any> = { ...(step.parameters ?? {}) };

    if (params.channelName) {
      const res = await EntityResolver.resolveChannel(ctx.guild, params.channelName);
      if (res.resolved) params.channelId = res.resolved.id;
    }
    if (params.roleName) {
      const res = await EntityResolver.resolveRole(ctx.guild, params.roleName);
      if (res.resolved) params.roleId = res.resolved.id;
    }

    const dispatchRes = await ActionDispatcher.dispatch(step.action, params, ctx);

    if (dispatchRes.requiresConfirmation && dispatchRes.confirmationDetails) {
      const plan = { type: PLAN_TYPE, steps, index: i };
      const planHash = PlanHasher.computeHash(plan);
      const actionNonce = PlanHasher.generateNonce();
      await ConfirmationRepository.create({
        guildId: ctx.guildId,
        userId: ctx.userId,
        planHash,
        actionNonce,
        actionPlan: plan,
      });
      return {
        completed: false,
        results,
        confirmation: {
          nonce: actionNonce,
          actionType: step.action,
          riskLevel: dispatchRes.confirmationDetails.riskLevel,
          stepLabel: `${i + 1}/${steps.length}`,
        },
      };
    }

    results.push({
      stepId: step.id,
      action: step.action,
      ok: dispatchRes.success,
      result: dispatchRes.result,
      error: dispatchRes.error,
    });

    if (!dispatchRes.success) {
      return { completed: true, results };
    }
  }

  return { completed: true, results };
}
