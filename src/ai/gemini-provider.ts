import { GoogleGenAI } from '@google/genai';
import { LLMProvider, ParsedIntent, ParsedIntentSchema, IntentStatus } from './types.js';
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';

export class GeminiLLMProvider implements LLMProvider {
  private ai: GoogleGenAI;

  constructor() {
    this.ai = new GoogleGenAI({ apiKey: config.GEMINI_API_KEY });
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
      const response = await this.ai.models.generateContent({
        model: config.GEMINI_MODEL,
        contents: [
          { role: 'user', parts: [{ text: `${systemPrompt}\nUser Request: "${prompt}"` }] }
        ],
        config: {
          responseMimeType: 'application/json',
        },
      });

      const responseText = response.text || '';
      const parsedJson = JSON.parse(responseText.trim());
      return ParsedIntentSchema.parse(parsedJson);
    } catch (error: any) {
      logger.error({ err: error }, 'Gemini parsing error or schema mismatch');
      return {
        status: IntentStatus.REJECTED,
        reason: 'Unable to parse natural language request safely with Gemini model.',
      };
    }
  }
}
