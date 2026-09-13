import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder, ModalBuilder, TextInputBuilder, TextInputStyle } from 'discord.js';

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

  static createQuestionEmbed(question: string, pendingId: string) {
    const embed = new EmbedBuilder()
      .setTitle('❓ Quick question')
      .setColor(0x3498db)
      .setDescription(question)
      .setFooter({ text: 'Hit Answer below — expires in 15 minutes.' });

    const answerButton = new ButtonBuilder()
      .setCustomId(`clarify-answer:${pendingId}`)
      .setLabel('Answer')
      .setStyle(ButtonStyle.Primary);

    const row = new ActionRowBuilder<ButtonBuilder>().addComponents(answerButton);

    return { embeds: [embed], components: [row] };
  }

  static createAnswerModal(pendingId: string, question: string) {
    const input = new TextInputBuilder()
      .setCustomId('answer')
      .setLabel('Your answer')
      .setStyle(TextInputStyle.Paragraph)
      .setRequired(true)
      .setMaxLength(1000)
      .setPlaceholder(question.slice(0, 100));

    const row = new ActionRowBuilder<TextInputBuilder>().addComponents(input);

    return new ModalBuilder()
      .setCustomId(`clarify-modal:${pendingId}`)
      .setTitle('Answer needed')
      .addComponents(row);
  }

  static createSuccessEmbed(title: string, description: string) {    const embed = new EmbedBuilder()
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
