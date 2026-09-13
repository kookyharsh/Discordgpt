import { LLMProvider, LLMContext, ParsedIntent, ParsedIntentSchema, IntentStatus } from './types.js';
import { historyBlock } from './conversation-context.js';
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

    try {
      const rawContent = await this.complete(
        [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: `User Request: "${prompt}"` },
        ],
        true,
        prompt
      );

      const parsedJson = JSON.parse(extractJson(rawContent));
      return ParsedIntentSchema.parse(parsedJson);
    } catch (error: any) {
      logger.error(
        { err: error?.message ?? error, provider: this.providerName, model: this.model },
        `${this.providerName} parsing error or schema mismatch`
      );
      return {
        status: IntentStatus.REJECTED,
        reason: friendlyReason(this.providerName, error),
      };
    }
  }

  async chat(prompt: string, context: LLMContext): Promise<string> {
    const startedAt = Date.now();
    try {
      const text = await this.complete(
        [
          {
            role: 'system',
            content: `You are GPTcord, a friendly and concise Discord server assistant. Answer questions, explain things, and help with server management advice. Use the server context (channels, roles) when relevant. Keep replies under 1500 characters. NEVER claim you executed a server action.\n\nServer channels: ${JSON.stringify(context.channels)}\nServer roles: ${JSON.stringify(context.roles)}\n${historyBlock(context.history)}`,
          },
          { role: 'user', content: prompt },
        ],
        false,
        prompt
      );
      const reply = text.trim().slice(0, 1900);
      if (!reply) throw new Error(`Empty completion from ${this.providerName}`);
      return reply;
    } catch (error: any) {
      logger.error(
        { err: error?.message ?? error, provider: this.providerName, latencyMs: Date.now() - startedAt },
        'Chat completion failed'
      );
      return 'Sorry, I could not think of a reply just now. Try again in a moment.';
    }
  }

  /** POST with json-mode fallback + one transient retry. Returns message content. */
  private async complete(
    messages: Array<{ role: string; content: string }>,
    withJsonMode: boolean,
    promptForLog: string
  ): Promise<string> {
    const endpoint = `${this.baseUrl}/chat/completions`;
    const startedAt = Date.now();
    logger.debug(
      { provider: this.providerName, model: this.model, promptLen: promptForLog.length },
      'llm request'
    );
    const baseBody: Record<string, unknown> = { model: this.model, messages };

    const post = (jsonMode: boolean, timeoutMs = 45000) => {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(new Error('LLM request timed out')), timeoutMs);
      return fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
          'HTTP-Referer': 'https://discord-natural-language-agent',
          'X-Title': 'Discord Natural Language Agent',
        },
        body: JSON.stringify(jsonMode ? { ...baseBody, response_format: { type: 'json_object' } } : baseBody),
        signal: ctrl.signal,
      }).finally(() => clearTimeout(timer));
    };

    // Some models (esp. free-tier) reject response_format; retry without it.
    let response = await post(withJsonMode);
    if (withJsonMode && response.status === 400) {
      const probe = await response.text();
      if (/response_format|json_object|json mode/i.test(probe)) {
        logger.warn({ provider: this.providerName }, 'Model rejected response_format, retrying without json mode');
        response = await post(false);
      } else {
        throw new Error(`HTTP 400 from ${this.providerName}: ${probe.slice(0, 200)}`);
      }
    }

    // Free-tier models are often rate-limited (429) or briefly unavailable (502/503); one retry.
    if ([429, 502, 503].includes(response.status)) {
      const firstErr = await response.text();
      logger.warn(
        { provider: this.providerName, status: response.status },
        'LLM transient error, retrying once after 2s'
      );
      await new Promise((r) => setTimeout(r, 2000));
      response = await post(false);
      if (!response.ok) {
        const retryErr = await response.text();
        throw new Error(
          `HTTP ${response.status} from ${this.providerName}: ${(retryErr || firstErr).slice(0, 200)}`
        );
      }
    } else if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status} from ${this.providerName}: ${errorText.slice(0, 200)}`);
    }

    const data: any = await response.json();
    const rawContent = data.choices?.[0]?.message?.content || '';
    logger.debug(
      { provider: this.providerName, latencyMs: Date.now() - startedAt, contentHead: String(rawContent).slice(0, 500) },
      'llm response'
    );
    if (!String(rawContent).trim()) {
      throw new Error(`Empty completion from ${this.providerName} (model ${this.model})`);
    }
    return String(rawContent);
  }
}

/** Strip fences, then scan for the first balanced {...} block (models add prose). */
function extractJson(raw: string): string {
  const fenced = raw.replace(/^```(json)?\s*/i, '').replace(/\s*```$/i, '').trim();
  try {
    JSON.parse(fenced);
    return fenced;
  } catch {
    // fall through to brace scan
  }
  const start = fenced.indexOf('{');
  if (start === -1) return fenced;
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let i = start; i < fenced.length; i++) {
    const ch = fenced[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === '"') inString = false;
    } else {
      if (ch === '"') inString = true;
      else if (ch === '{') depth++;
      else if (ch === '}') {
        depth--;
        if (depth === 0) return fenced.slice(start, i + 1);
      }
    }
  }
  return fenced;
}

/** Short, user-facing reason with no secret material (API error bodies carry none). */
function friendlyReason(provider: string, error: any): string {
  const msg = String(error?.message ?? error ?? '');
  if (/HTTP 429/.test(msg)) {
    return `${provider} is rate-limited right now (free-tier upstream limit). Wait ~1 min and retry; simple commands (create channel/role, ban, timeout) still work offline.`;
  }
  if (/timed out|TimeoutError|aborted|abort/i.test(msg)) {
    return `${provider} took too long to respond (45s timeout). Retry once; if it persists try a different model.`;
  }
  if (/HTTP 401|invalid.*key|unauthorized/i.test(msg)) {
    return `${provider} rejected the API key (HTTP 401). Check OPENROUTER_API_KEY/OPENAI_API_KEY in .env.`;
  }
  if (/HTTP 404|No endpoints|model/i.test(msg) && /404/.test(msg)) {
    return `${provider} model not found (HTTP 404). Check OPENROUTER_MODEL in .env.`;
  }
  if (/Empty completion/.test(msg)) {
    return `${provider} returned an empty reply. Retry once; if it persists try a different model.`;
  }
  const short = msg.replace(/\s+/g, ' ').slice(0, 180);
  return `Unable to parse request safely with ${provider} model${short ? `: ${short}` : '.'}`;
}
