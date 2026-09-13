import { z } from 'zod';
import { PermissionFlagsBits, TextChannel } from 'discord.js';
import { ActionDefinition, ConfirmationPolicy, RiskLevel } from './types.js';
import { ActionRegistry } from './registry.js';

export const sendMessageAction: ActionDefinition = {
  type: 'send_message',
  description: 'Sends a message to a specific channel.',
  inputSchema: z.object({
    channelId: z.string(),
    content: z.string().min(1).max(2000),
  }),
  requiredBotPermissions: [PermissionFlagsBits.SendMessages],
  requiredUserPermissions: [PermissionFlagsBits.SendMessages],
  riskLevel: RiskLevel.LOW,
  confirmationPolicy: ConfirmationPolicy.NOT_REQUIRED,
  handler: async (ctx, input) => {
    const channel = await ctx.guild.channels.fetch(input.channelId);
    if (!channel || !channel.isTextBased()) {
      throw new Error(`Text channel ${input.channelId} not found.`);
    }

    const message = await (channel as TextChannel).send(input.content);

    return {
      messageId: message.id,
      channelId: channel.id,
      sent: true,
    };
  },
};

ActionRegistry.register(sendMessageAction);
