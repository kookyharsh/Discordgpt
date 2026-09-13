import { ExecutionContext, RiskLevel, ConfirmationPolicy } from './types.js';
import { ActionRegistry } from './registry.js';
import { PermissionEngine } from '../permissions/permission-engine.js';
import { GuildPolicyEngine } from '../policies/guild-policy.js';
import { TenantGuard } from '../security/tenant-guard.js';
import { AuditRepository, ConfirmationRepository } from '../database/repositories.js';
import { PlanHasher } from '../security/plan-hasher.js';

export interface DispatchResult {
  success: boolean;
  requiresConfirmation?: boolean;
  confirmationDetails?: {
    actionNonce: string;
    planHash: string;
    actionType: string;
    riskLevel: RiskLevel;
  };
  result?: any;
  error?: string;
}

export class ActionDispatcher {
  static async dispatch(
    actionType: string,
    parameters: any,
    ctx: ExecutionContext
  ): Promise<DispatchResult> {
    TenantGuard.validateGuildBoundary(ctx.guildId, ctx.guild.id);

    const action = ActionRegistry.get(actionType);
    if (!action) {
      return {
        success: false,
        error: `Unknown or unregistered action type: '${actionType}'. No dynamic fallback code execution is permitted.`,
      };
    }

    const parseResult = action.inputSchema.safeParse(parameters);
    if (!parseResult.success) {
      return {
        success: false,
        error: `Invalid input parameters for action '${actionType}': ${parseResult.error.message}`,
      };
    }
    const validatedInput = parseResult.data;

    const policyCheck = GuildPolicyEngine.checkActionAllowed(actionType, ctx.settings);
    if (!policyCheck.allowed) {
      return {
        success: false,
        error: policyCheck.reason,
      };
    }

    const botPermCheck = await PermissionEngine.checkBotPermissions(ctx.guild, action.requiredBotPermissions);
    if (!botPermCheck.allowed) {
      return {
        success: false,
        error: botPermCheck.reason,
      };
    }

    const userPermCheck = PermissionEngine.checkUserPermissions(ctx.actorMember, action.requiredUserPermissions);
    if (!userPermCheck.allowed) {
      return {
        success: false,
        error: userPermCheck.reason,
      };
    }

    const isDangerous = action.riskLevel === RiskLevel.HIGH || action.riskLevel === RiskLevel.CRITICAL;
    const needsConfirmation = action.confirmationPolicy === ConfirmationPolicy.ALWAYS_CONFIRM ||
      (action.confirmationPolicy === ConfirmationPolicy.REQUIRED && isDangerous);

    if (needsConfirmation) {
      const plan = { type: actionType, input: validatedInput };
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
        success: false,
        requiresConfirmation: true,
        confirmationDetails: {
          actionNonce,
          planHash,
          actionType,
          riskLevel: action.riskLevel,
        },
      };
    }

    try {
      const handlerResult = await action.handler(ctx, validatedInput);

      await AuditRepository.log({
        guildId: ctx.guildId,
        userId: ctx.userId,
        executionId: ctx.executionId,
        action: actionType,
        parameters: validatedInput,
        result: handlerResult,
        status: 'SUCCESS',
      });

      return {
        success: true,
        result: handlerResult,
      };
    } catch (error: any) {
      await AuditRepository.log({
        guildId: ctx.guildId,
        userId: ctx.userId,
        executionId: ctx.executionId,
        action: actionType,
        parameters: validatedInput,
        status: 'FAILURE',
        error: error.message,
      });

      return {
        success: false,
        error: error.message || 'Action handler execution failed.',
      };
    }
  }
}
