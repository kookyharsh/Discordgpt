import { ActionDefinition } from './types.js';

export class ActionRegistry {
  private static actions: Map<string, ActionDefinition> = new Map();

  static register(action: ActionDefinition) {
    if (this.actions.has(action.type)) {
      throw new Error(`Action '${action.type}' is already registered.`);
    }
    this.actions.set(action.type, action);
  }

  static get(type: string): ActionDefinition | undefined {
    return this.actions.get(type);
  }

  static getAll(): ActionDefinition[] {
    return Array.from(this.actions.values());
  }

  static isRegistered(type: string): boolean {
    return this.actions.has(type);
  }
}
