import { prisma } from '../database/prisma.js';
import { ActionDispatcher, DispatchResult } from './dispatcher.js';
import { ExecutionContext } from './types.js';

export class SavedCommandRouter {
  static async saveCommand(
    guildId: string,
    createdByUserId: string,
    name: string,
    description: string,
    actionPlan: any
  ) {
    const cleanedName = name.trim().toLowerCase().replace(/[^a-z0-9-_]/g, '');

    return prisma.generatedCommand.upsert({
      where: {
        guildId_name: {
          guildId,
          name: cleanedName,
        },
      },
      create: {
        guildId,
        createdByUserId,
        name: cleanedName,
        description,
        actionPlan,
      },
      update: {
        description,
        actionPlan,
        createdByUserId,
      },
    });
  }

  static async executeSavedCommand(
    name: string,
    ctx: ExecutionContext
  ): Promise<DispatchResult> {
    const cleanedName = name.trim().toLowerCase();

    const saved = await prisma.generatedCommand.findUnique({
      where: {
        guildId_name: {
          guildId: ctx.guildId,
          name: cleanedName,
        },
      },
    });

    if (!saved || !saved.enabled) {
      return {
        success: false,
        error: `Saved command '/${cleanedName}' not found or disabled in this server.`,
      };
    }

    const plan = saved.actionPlan as any;
    if (!plan || !plan.type) {
      return {
        success: false,
        error: `Saved command '/${cleanedName}' has an invalid action plan definition.`,
      };
    }

    return ActionDispatcher.dispatch(plan.type, plan.input, ctx);
  }
}
