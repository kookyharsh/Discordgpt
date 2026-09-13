import crypto from 'crypto';
import { ActionRegistry } from '../actions/registry.js';
import { DispatchPlan } from '../actions/dispatcher.js';

export interface ConfirmationDetails {
  id: string;
  guildId: string;
  userId: string;
  plan: DispatchPlan;
  planHash: string;
  nonce: string;
  expiresAt: number;
  consumed: boolean;
}

export class ConfirmationManager {
  private static store: Map<string, ConfirmationDetails> = new Map();
  public static readonly CONFIRMATION_EXPIRATION_MS = 5 * 60 * 1000; // 5 minutes

  public static hashPlan(plan: DispatchPlan): string {
    const serialized = JSON.stringify(plan);
    return crypto.createHash('sha256').update(serialized).digest('hex');
  }

  public static requiresConfirmation(plan: DispatchPlan): boolean {
    for (const step of plan.steps) {
      const actDef = ActionRegistry.get(step.action);
      if (actDef && actDef.confirmationPolicy === 'REQUIRED') {
        return true;
      }
      if (actDef && (actDef.riskLevel === 'HIGH' || actDef.riskLevel === 'CRITICAL')) {
        return true;
      }
    }
    return false;
  }

  public static createConfirmation(guildId: string, userId: string, plan: DispatchPlan): ConfirmationDetails {
    const nonce = crypto.randomBytes(16).toString('hex');
    const id = `conf-${Date.now()}-${nonce.substring(0, 8)}`;
    const planHash = this.hashPlan(plan);
    const expiresAt = Date.now() + this.CONFIRMATION_EXPIRATION_MS;

    const details: ConfirmationDetails = {
      id,
      guildId,
      userId,
      plan,
      planHash,
      nonce,
      expiresAt,
      consumed: false,
    };

    this.store.set(id, details);
    return details;
  }

  public static validateAndConsumeConfirmation(
    confirmationId: string,
    guildId: string,
    userId: string,
    plan: DispatchPlan
  ): { valid: boolean; reason?: string } {
    const details = this.store.get(confirmationId);
    if (!details) {
      return { valid: false, reason: 'Confirmation request not found.' };
    }

    if (details.consumed) {
      return { valid: false, reason: 'This confirmation request has already been used.' };
    }

    if (Date.now() > details.expiresAt) {
      return { valid: false, reason: 'This confirmation request has expired. Please submit your request again.' };
    }

    if (details.guildId !== guildId || details.userId !== userId) {
      return { valid: false, reason: 'Confirmation request tenant or user mismatch.' };
    }

    const currentHash = this.hashPlan(plan);
    if (currentHash !== details.planHash) {
      return { valid: false, reason: 'Action plan hash mismatch. The target action parameters were altered.' };
    }

    // Mark as consumed (Single-use replay protection)
    details.consumed = true;
    this.store.set(confirmationId, details);

    return { valid: true };
  }
}
