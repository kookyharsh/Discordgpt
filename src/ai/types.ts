export interface LLMRequestOptions {
  prompt: string;
  systemPrompt?: string;
  temperature?: number;
  maxTokens?: number;
}

export interface LLMProvider {
  name: string;
  generateCompletion(options: LLMRequestOptions): Promise<string>;
}
