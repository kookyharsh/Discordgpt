import crypto from 'crypto';

export class PlanHasher {
  static computeHash(actionPlan: any): string {
    const serialized = JSON.stringify(actionPlan, Object.keys(actionPlan).sort());
    return crypto.createHash('sha256').update(serialized).digest('hex');
  }

  static generateNonce(): string {
    return crypto.randomBytes(16).toString('hex');
  }
}
