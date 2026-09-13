import { ActionRegistry } from './registry.js';
import { ExecutionContext } from './types.js';

export interface DispatchStep {
  id: string;
  action: string;
  parameters: any;
}

export interface DispatchPlan {
  steps: DispatchStep[];
}

export interface StepResult {
  stepId: string;
  action: string;
  status: 'SUCCESS' | 'FAILED';
  result?: any;
  error?: string;
}

export interface DispatchResult {
  executionId: string;
  status: 'COMPLETED' | 'PARTIAL_FAILURE' | 'FAILED';
  stepResults: StepResult[];
  createdResources: Array<{ type: string; id: string }>;
  error?: string;
}

export class ActionDispatcher {
  async dispatch(plan: DispatchPlan, ctx: ExecutionContext): Promise<DispatchResult> {
    const stepResults: StepResult[] = [];
    ctx.createdResources = ctx.createdResources || [];
    let hasFailure = false;

    for (const step of plan.steps) {
      const actionDef = ActionRegistry.get(step.action);
      if (!actionDef) {
        const errorMsg = `UnknownActionError: '${step.action}' is not registered in Action Registry.`;
        stepResults.push({
          stepId: step.id,
          action: step.action,
          status: 'FAILED',
          error: errorMsg,
        });
        hasFailure = true;
        break; // Stop execution on failure
      }

      // Schema Validation
      const parseResult = actionDef.inputSchema.safeParse(step.parameters);
      if (!parseResult.success) {
        const errorMsg = `InvalidInputError: ${parseResult.error.message}`;
        stepResults.push({
          stepId: step.id,
          action: step.action,
          status: 'FAILED',
          error: errorMsg,
        });
        hasFailure = true;
        break;
      }

      // Execute Handler
      try {
        const result = await actionDef.handler(ctx, parseResult.data);
        stepResults.push({
          stepId: step.id,
          action: step.action,
          status: 'SUCCESS',
          result,
        });
      } catch (err: any) {
        const errorMsg = err?.message || 'Execution error';
        stepResults.push({
          stepId: step.id,
          action: step.action,
          status: 'FAILED',
          error: errorMsg,
        });
        hasFailure = true;
        break; // Stop multi-step plan on partial failure
      }
    }

    let overallStatus: 'COMPLETED' | 'PARTIAL_FAILURE' | 'FAILED' = 'COMPLETED';
    if (hasFailure) {
      const successfulCount = stepResults.filter((s) => s.status === 'SUCCESS').length;
      overallStatus = successfulCount > 0 ? 'PARTIAL_FAILURE' : 'FAILED';

      // Rollback created resources if safe
      if (ctx.createdResources.length > 0) {
        ctx.logger.info(`Rolling back ${ctx.createdResources.length} resources created in execution ${ctx.executionId}`);
        for (const res of [...ctx.createdResources].reverse()) {
          const actDef = Array.from(ActionRegistry.getAll()).find((a) => a.rollback);
          if (actDef && actDef.rollback) {
            try {
              await actDef.rollback(ctx, res.id);
            } catch (rbErr) {
              ctx.logger.error(`Rollback failed for resource ${res.id}: ${rbErr}`);
            }
          }
        }
      }
    }

    return {
      executionId: ctx.executionId,
      status: overallStatus,
      stepResults,
      createdResources: ctx.createdResources,
      error: hasFailure ? stepResults.find((s) => s.status === 'FAILED')?.error : undefined,
    };
  }
}
