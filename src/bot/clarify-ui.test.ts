import { describe, it, expect } from 'vitest';
import { DiscordUIComponents } from './ui.js';

describe('clarification UI', () => {
  it('builds a question embed with an answer button', () => {
    const ui = DiscordUIComponents.createQuestionEmbed('Which channel?', 'pending-123');
    expect(ui.embeds).toHaveLength(1);
    expect(ui.components).toHaveLength(1);
    const button = (ui.components[0] as any).components[0];
    expect(button.data.custom_id).toBe('clarify-answer:pending-123');
  });

  it('builds an answer modal with matching id', () => {
    const modal = DiscordUIComponents.createAnswerModal('pending-123', 'Which channel?');
    expect(modal.data.custom_id).toBe('clarify-modal:pending-123');
    const input = (modal.components[0] as any).components[0];
    expect(input.data.custom_id).toBe('answer');
  });
});
