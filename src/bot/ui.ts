import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder } from 'discord.js';

export class DiscordUIComponents {
  static createConfirmationEmbed(
    actionType: string,
    riskLevel: string,
    planDetails: string,
    nonce: string
  ) {
    const embed = new EmbedBuilder()
      .setTitle(`⚠️ Confirmation Required: ${actionType}`)
      .setColor(riskLevel === 'CRITICAL' || riskLevel === 'HIGH' ? 0xff0000 : 0xffa500)
      .setDescription(`The requested action involves potential server mutations.\n\n**Action Details:**\n${planDetails}`)
      .addFields(
        { name: 'Risk Level', value: riskLevel, inline: true },
        { name: 'Expiration', value: '5 minutes', inline: true }
      )
      .setFooter({ text: `Action Nonce: ${nonce}` });

    const confirmButton = new ButtonBuilder()
      .setCustomId(`confirm:${nonce}`)
      .setLabel('Confirm & Execute')
      .setStyle(ButtonStyle.Danger);

    const cancelButton = new ButtonBuilder()
      .setCustomId(`cancel:${nonce}`)
      .setLabel('Cancel')
      .setStyle(ButtonStyle.Secondary);

    const row = new ActionRowBuilder<ButtonBuilder>().addComponents(confirmButton, cancelButton);

    return { embeds: [embed], components: [row] };
  }

  static createDisambiguationEmbed(
    title: string,
    description: string,
    customId: string,
    options: Array<{ label: string; value: string; description?: string }>
  ) {
    const embed = new EmbedBuilder()
      .setTitle(`ℹ️ Clarification Needed: ${title}`)
      .setColor(0x3498db)
      .setDescription(description);

    const selectMenu = new StringSelectMenuBuilder()
      .setCustomId(customId)
      .setPlaceholder('Select an option...')
      .addOptions(
        options.slice(0, 25).map((opt) => ({
          label: opt.label,
          value: opt.value,
          description: opt.description,
        }))
      );

    const row = new ActionRowBuilder<StringSelectMenuBuilder>().addComponents(selectMenu);

    return { embeds: [embed], components: [row] };
  }

  static createSuccessEmbed(title: string, description: string) {
    const embed = new EmbedBuilder()
      .setTitle(`✅ ${title}`)
      .setColor(0x2ecc71)
      .setDescription(description);

    return { embeds: [embed], components: [] };
  }

  static createErrorEmbed(title: string, reason: string) {
    const embed = new EmbedBuilder()
      .setTitle(`❌ ${title}`)
      .setColor(0xe74c3c)
      .setDescription(`**Reason:** ${reason}\n\n*No changes were made.*`);

    return { embeds: [embed], components: [] };
  }
}
