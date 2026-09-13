import { LLMProvider, ParsedIntent, ParsedIntentSchema, IntentStatus } from './types.js';
import { logger } from '../utils/logger.js';

export interface OpenAILLMProviderOptions {
  apiKey: string;
  baseUrl: string;
  model: string;
  providerName?: string;
}

export class OpenAILLMProvider implements LLMProvider {
  private apiKey: string;
  private baseUrl: string;
  private model: string;
  private providerName: string;

  constructor(options: OpenAILLMProviderOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.model = options.model;
    this.providerName = options.providerName || 'OpenAI-Compatible';
  }

  async parseIntent(
    prompt: string,
    context: {
      guildId: string;
      channels: Array<{ id: string; name: string }>;
      roles: Array<{ id: string; name: string }>;
      allowedActions: string[];
    }
  ): Promise<ParsedIntent> {
    const systemPrompt = `
You are a Discord action planner.
You do NOT execute actions.
You do NOT have direct access to Discord APIs.
You may ONLY select actions from the supplied allowed actions catalog: ${JSON.stringify(context.allowedActions)}.
You must NEVER invent an action name.
You must NEVER return source code, JavaScript, TypeScript, shell script, or executable code.

Rules:
1. If the request is dangerous or unsupported (e.g. changing passwords, running scripts, accessing host), set status to "unsupported" or "rejected".
2. If required details (e.g. channel name, user target) are missing, set status to "clarification_required" and ask a concise question.
3. If the request matches a supported action, set status to "direct_action" or "action_plan".
4. Output strict JSON conforming to the schema. Do NOT include markdown code fences or extra commentary outside JSON.

Context channels: ${JSON.stringify(context.channels)}
Context roles: ${JSON.stringify(context.roles)}
`;

    try {
      const endpoint = `${this.baseUrl}/chat/completions`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
          'HTTP-Referer': 'https://discord-natural-language-agent',
          'X-Title': 'Discord Natural Language Agent',
        },
        body: JSON.stringify({
          model: this.model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: `User Request: "${prompt}"` },
          ],
          response_format: { type: 'json_object' },
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status} from ${this.providerName}: ${errorText}`);
      }

      const data: any = await response.json();
      const rawContent = data.choices?.[0]?.message?.content || '';

      // Clean markdown code blocks if the model wrapped the JSON
      const jsonContent = rawContent.replace(/^```(json)?\s*/i, '').replace(/\s*```$/i, '').trim();

      const parsedJson = JSON.parse(jsonContent);
      return ParsedIntentSchema.parse(parsedJson);
    } catch (error: any) {
      logger.error({ err: error, provider: this.providerName }, `${this.providerName} parsing error or schema mismatch`);
      return {
        status: IntentStatus.REJECTED,
        reason: `Unable to parse natural language request safely with ${this.providerName} model.`,
      };
    }
  }
}
