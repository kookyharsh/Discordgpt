import OpenAI from 'openai';
import { LLMProvider, LLMRequestOptions } from '../types.js';

export class OpenAIProvider implements LLMProvider {
  name = 'openai';
  private client: OpenAI;

  constructor(apiKey?: string, private model: string = 'gpt-4o') {
    this.client = new OpenAI({ apiKey: apiKey || process.env.OPENAI_API_KEY || process.env.LLM_API_KEY });
  }

  async generateCompletion(options: LLMRequestOptions): Promise<string> {
    const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [];
    if (options.systemPrompt) {
      messages.push({ role: 'system', content: options.systemPrompt });
    }
    messages.push({ role: 'user', content: options.prompt });

    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options.temperature ?? 0,
      response_format: { type: 'json_object' },
    });

    return response.choices[0]?.message?.content || '{}';
  }
}
