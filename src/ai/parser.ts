import { LLMProvider } from './types.js';
import { ParsedIntent, ParsedIntentSchema } from './intent-schema.js';
import { SYSTEM_PROMPT } from './prompts.js';
import { ActionRegistry } from '../actions/registry.js';
import { PromptInjectionDefense } from '../security/injection-defense.js';

export class NaturalLanguageParser {
  constructor(private llmProvider: LLMProvider) {}

  public parseDeterministic(prompt: string): ParsedIntent | null {
    const cleanPrompt = prompt.trim().toLowerCase();

    // Deterministic: "create channel <name>"
    const createChanMatch = cleanPrompt.match(/^create channel\s+(?:called\s+)?([a-z0-9-_]+)$/i);
    if (createChanMatch) {
      return {
        status: 'direct_action',
        intentType: 'single_action',
        action: 'create_channel',
        parameters: { name: createChanMatch[1] },
      };
    }

    // Deterministic unsupported requests
    if (
      cleanPrompt.includes('python') ||
      cleanPrompt.includes('javascript') ||
      cleanPrompt.includes('run script') ||
      cleanPrompt.includes('open chrome') ||
      cleanPrompt.includes('password') ||
      cleanPrompt.includes('send email') ||
      cleanPrompt.includes('rm -rf')
    ) {
      return {
        status: 'unsupported',
        reason: 'Requested operation is outside supported Discord bot capabilities or involves arbitrary code/external execution.',
      };
    }

    // Deterministic data availability check: "ban everyone who hasn't spoken in 6 months"
    if (cleanPrompt.includes("hasn't spoken in") || cleanPrompt.includes('inactive for 6 months')) {
      return {
        status: 'capability_unavailable',
        reason: 'Discord does not provide enough reliable historical message activity data to determine member activity over 6 months with currently available gateway intents/API endpoints.',
      };
    }

    return null;
  }

  public async parseRequest(prompt: string, context?: any): Promise<ParsedIntent> {
    const sanitizedPrompt = PromptInjectionDefense.sanitizeInput(prompt);

    // 1. Stage 1: Deterministic Parsing
    const deterministicResult = this.parseDeterministic(sanitizedPrompt);
    if (deterministicResult) {
      return deterministicResult;
    }

    // Prompt injection check
    if (PromptInjectionDefense.detectInjectionAttempt(sanitizedPrompt)) {
      return {
        status: 'rejected',
        reason: 'Prompt contains unauthorized or potentially malicious system instructions.',
      };
    }

    // 2. Stage 2: LLM-assisted Parsing
    const actionCatalog = ActionRegistry.getAll().map((a) => ({
      action: a.type,
      description: a.description,
      requiredPermissions: a.requiredUserPermissions,
    }));

    const userPayload = JSON.stringify({
      prompt: sanitizedPrompt,
      context,
      actionCatalog,
    });

    try {
      const rawOutput = await this.llmProvider.generateCompletion({
        prompt: userPayload,
        systemPrompt: SYSTEM_PROMPT,
      });

      const parsedJson = JSON.parse(rawOutput);
      const validated = ParsedIntentSchema.safeParse(parsedJson);

      if (!validated.success) {
        return {
          status: 'rejected',
          reason: `Model output failed schema validation: ${validated.error.message}`,
        };
      }

      return validated.data;
    } catch (err: any) {
      return {
        status: 'rejected',
        reason: `Failed to parse natural language intent: ${err?.message || 'LLM service error'}`,
      };
    }
  }
}
