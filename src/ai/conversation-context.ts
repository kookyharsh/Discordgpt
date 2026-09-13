/** Renders recent conversation turns for LLM system prompts. */
export function historyBlock(history?: string[]): string {
  if (!history || history.length === 0) return 'Conversation history: (none)';
  return `Conversation history (oldest first):\n${history.join('\n')}`;
}
