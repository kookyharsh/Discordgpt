import Anthropic from '@anthropic-ai/sdk';
import { LLMProvider, LLMRequestOptions } from '../types.js';

export class ClaudeProvider implements LLMProvider {
  name = 'claude';
  private client: Anthropic;

  constructor(apiKey?: string, private model: string = 'claude-3-5-sonnet-20241022') {
    this.client = new Anthropic({ apiKey: apiKey || process.env.ANTHROPIC_API_KEY || process.env.LLM_API_KEY });
  }

  async generateCompletion(options: LLMRequestOptions): Promise<string> {
    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: options.maxTokens || 1024,
      system: options.systemPrompt,
      messages: [{ role: 'user', content: options.prompt }],
    });

    const firstBlock = response.content[0];
    return firstBlock.type === 'text' ? firstBlock.text : '{}';
  }
}
