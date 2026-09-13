export interface GuildPolicyConfig {
  enabled: boolean;
  disabledActions: string[];
  allowedActions: string[];
  maxMembersPerAction: number;
  maxChannelsPerAction: number;
  maxActionsPerRequest: number;
  confirmationMode: 'STRICT' | 'STANDARD';
}

export class PolicyEngine {
  public static readonly DEFAULT_POLICY: GuildPolicyConfig = {
    enabled: true,
    disabledActions: [],
    allowedActions: [],
    maxMembersPerAction: 25,
    maxChannelsPerAction: 10,
    maxActionsPerRequest: 10,
    confirmationMode: 'STRICT',
  };

  public static evaluatePolicy(policy: GuildPolicyConfig, actionType: string, affectedCount: number = 1): { allowed: boolean; reason?: string } {
    if (!policy.enabled) {
      return { allowed: false, reason: 'Bot operations are disabled for this guild.' };
    }

    if (policy.disabledActions.includes(actionType)) {
      return { allowed: false, reason: `This server administrator has disabled the '${actionType}' action.` };
    }

    if (policy.allowedActions.length > 0 && !policy.allowedActions.includes(actionType)) {
      return { allowed: false, reason: `Action '${actionType}' is not in this server's whitelist of allowed actions.` };
    }

    if (actionType.includes('channel') && affectedCount > policy.maxChannelsPerAction) {
      return {
        allowed: false,
        reason: `Operation affects ${affectedCount} channels, which exceeds the server limit of ${policy.maxChannelsPerAction}.`,
      };
    }

    if ((actionType.includes('member') || actionType.includes('user')) && affectedCount > policy.maxMembersPerAction) {
      return {
        allowed: false,
        reason: `Operation affects ${affectedCount} members, which exceeds the server limit of ${policy.maxMembersPerAction}.`,
      };
    }

    return { allowed: true };
  }
}
