import { GoogleGenAI } from '@google/genai';
import { LLMProvider, LLMContext, ParsedIntent, ParsedIntentSchema, IntentStatus } from './types.js';
import { historyBlock } from './conversation-context.js';
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';

export class GeminiLLMProvider implements LLMProvider {
  private ai: GoogleGenAI;

  constructor() {
    this.ai = new GoogleGenAI({ apiKey: config.GEMINI_API_KEY });
  }

  async parseIntent(prompt: string, context: LLMContext): Promise<ParsedIntent> {
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
3. If the request matches a supported action, set status to "direct_action" or "action_plan". For multi-step requests use "action_plan" with ordered steps ({id, action, parameters}), max 5 steps.
4. If the user is chatting, asking a question, or wants information with NO server action involved, set status to "chat" and put a helpful conversational reply in "message" (plain text, may reference server context; NEVER claim you executed an action).
5. Output strict JSON conforming to the schema. Do NOT include markdown code fences or extra commentary outside JSON.

Mention/ID convention (use these verbatim as IDs, NEVER invent snowflakes):
- <@123> is a member ID, <@&123> is a role ID, <#123> is a channel ID.
- Prefer these IDs in parameters (memberId, roleId, channelId). Otherwise use names and the bot resolves them.
- Never guess an ID that is not in the request; ask for it instead.

Context channels: ${JSON.stringify(context.channels)}
Context roles: ${JSON.stringify(context.roles)}
${historyBlock(context.history)}
`;

    const startedAt = Date.now();
    logger.debug(
      { model: config.GEMINI_MODEL, promptLen: prompt.length, channels: context.channels.length, roles: context.roles.length },
      'gemini request'
    );

    try {
      const response = await withTimeout(
        this.ai.models.generateContent({
          model: config.GEMINI_MODEL,
          contents: [
            { role: 'user', parts: [{ text: `${systemPrompt}\nUser Request: "${prompt}"` }] }
          ],
          config: {
            responseMimeType: 'application/json',
          },
        }),
        45000
      );

      const responseText = response.text || '';
      logger.debug(
        { latencyMs: Date.now() - startedAt, contentHead: responseText.slice(0, 500) },
        'gemini response'
      );
      if (!responseText.trim()) {
        throw new Error(`Empty completion from Gemini (model ${config.GEMINI_MODEL})`);
      }
      const parsedJson = JSON.parse(responseText.trim());
      return ParsedIntentSchema.parse(parsedJson);
    } catch (error: any) {
      const msg = String(error?.message ?? error ?? '');
      logger.error({ err: msg.slice(0, 300), model: config.GEMINI_MODEL }, 'Gemini parsing error or schema mismatch');
      let reason: string;
      if (/404|NOT_FOUND|no longer available/i.test(msg)) {
        reason = `Gemini model "${config.GEMINI_MODEL}" is unavailable (404 - retired or bad ID). Update GEMINI_MODEL in .env (e.g. gemini-3.6-flash).`;
      } else if (/401|API_KEY_INVALID|API key|unauthenticated|permission denied|403/i.test(msg)) {
        reason = 'Gemini rejected the API key. Check GEMINI_API_KEY in .env.';
      } else if (/429|RESOURCE_EXHAUSTED|quota/i.test(msg)) {
        reason = 'Gemini is rate-limited/quota-exceeded right now. Wait a bit and retry.';
      } else if (/timed out|TimeoutError|aborted|abort/i.test(msg)) {
        reason = `Gemini took too long to respond (45s timeout). Retry once; if it persists try a different model.`;
      } else if (/Empty completion/.test(msg)) {
        reason = 'Gemini returned an empty reply. Retry once; if it persists try a different model.';
      } else {
        const short = msg.replace(/\s+/g, ' ').slice(0, 180);
        reason = `Unable to parse request safely with Gemini model${short ? `: ${short}` : '.'}`;
      }
      return { status: IntentStatus.REJECTED, reason };
    }
  }

  async chat(prompt: string, context: LLMContext): Promise<string> {
    const startedAt = Date.now();
    try {
      const response = await withTimeout(
        this.ai.models.generateContent({
          model: config.GEMINI_MODEL,
          contents: [
            {
              role: 'user',
              parts: [
                {
                  text: `You are GPTcord, a friendly and concise Discord server assistant. Answer questions, explain things, and help with server management advice. Use the server context when relevant. Keep replies under 1500 characters. NEVER claim you executed a server action.\n\nServer channels: ${JSON.stringify(context.channels)}\nServer roles: ${JSON.stringify(context.roles)}\n${historyBlock(context.history)}\n\nUser: ${prompt}`,
                },
              ],
            },
          ],
        }),
        45000
      );
      const reply = (response.text || '').trim().slice(0, 1900);
      if (!reply) throw new Error('Empty completion from Gemini');
      return reply;
    } catch (error: any) {
      logger.error(
        { err: String(error?.message ?? error).slice(0, 200), latencyMs: Date.now() - startedAt },
        'Gemini chat failed'
      );
      return 'Sorry, I could not think of a reply just now. Try again in a moment.';
    }
  }
}

/** The SDK call has no built-in timeout - cap it so "thinking" can never hang forever. */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Gemini request timed out after ${ms}ms`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer!));
}
