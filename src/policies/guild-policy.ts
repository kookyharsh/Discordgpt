export interface PolicyCheckResult {
  allowed: boolean;
  reason?: string;
}

export class GuildPolicyEngine {
  static checkActionAllowed(
    actionType: string,
    settings?: {
      enabled?: boolean;
      allowedActions?: string[];
      disabledActions?: string[];
    } | null
  ): PolicyCheckResult {
    if (!settings) return { allowed: true };

    if (settings.enabled === false) {
      return { allowed: false, reason: 'Bot interactions are currently disabled for this server.' };
    }

    if (settings.disabledActions && settings.disabledActions.includes(actionType)) {
      return { allowed: false, reason: `Action '${actionType}' has been disabled by server administrators.` };
    }

    if (
      settings.allowedActions &&
      settings.allowedActions.length > 0 &&
      !settings.allowedActions.includes(actionType)
    ) {
      return { allowed: false, reason: `Action '${actionType}' is not in the server's allowed actions list.` };
    }

    return { allowed: true };
  }
}
