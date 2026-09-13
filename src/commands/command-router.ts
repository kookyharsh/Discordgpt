import { ActionDispatcher, DispatchPlan } from '../actions/dispatcher.js';
import { ExecutionContext } from '../actions/types.js';
import { PermissionEngine } from '../permissions/permission-engine.js';
import { PolicyEngine, GuildPolicyConfig } from '../policies/policy-engine.js';

export interface SavedCommandDefinition {
  id: string;
  guildId: string;
  name: string;
  description: string;
  createdByUserId: string;
  plan: DispatchPlan;
  enabled: boolean;
}

export class SavedCommandRouter {
  private commands: Map<string, SavedCommandDefinition> = new Map();

  constructor(
    private dispatcher: ActionDispatcher,
    private permissionEngine: PermissionEngine
  ) {}

  public saveCommand(cmd: SavedCommandDefinition): void {
    // Keyed by guildId + name to ensure strict multi-tenant isolation
    const key = `${cmd.guildId}:${cmd.name.toLowerCase()}`;
    this.commands.set(key, cmd);
  }

  public getCommand(guildId: string, name: string): SavedCommandDefinition | undefined {
    return this.commands.get(`${guildId}:${name.toLowerCase()}`);
  }

  public listCommands(guildId: string): SavedCommandDefinition[] {
    return Array.from(this.commands.values()).filter((c) => c.guildId === guildId);
  }

  public deleteCommand(guildId: string, name: string): boolean {
    return this.commands.delete(`${guildId}:${name.toLowerCase()}`);
  }

  public async executeCommand(
    guildId: string,
    userId: string,
    commandName: string,
    ctx: ExecutionContext,
    policy: GuildPolicyConfig
  ): Promise<any> {
    const cmd = this.getCommand(guildId, commandName);
    if (!cmd || !cmd.enabled) {
      throw new Error(`Saved command '/${commandName}' not found or disabled in this server.`);
    }

    // 1. Verify Policy
    for (const step of cmd.plan.steps) {
      const polEval = PolicyEngine.evaluatePolicy(policy, step.action);
      if (!polEval.allowed) {
        throw new Error(`Policy error: ${polEval.reason}`);
      }

      // 2. Verify Permissions
      const permEval = await this.permissionEngine.checkActionPermissions(guildId, userId, step.action);
      if (!permEval.allowed) {
        throw new Error(`Permission error: ${permEval.reason}`);
      }
    }

    // 3. Execute Action Plan deterministically (NO arbitrary code execution)
    return this.dispatcher.dispatch(cmd.plan, ctx);
  }
}
