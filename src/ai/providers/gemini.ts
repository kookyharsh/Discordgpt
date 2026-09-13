import { GoogleGenerativeAI } from '@google/generative-ai';
import { LLMProvider, LLMRequestOptions } from '../types.js';

export class GeminiProvider implements LLMProvider {
  name = 'gemini';
  private ai: GoogleGenerativeAI;

  constructor(apiKey?: string, private modelName: string = 'gemini-1.5-pro') {
    this.ai = new GoogleGenerativeAI(apiKey || process.env.GEMINI_API_KEY || process.env.LLM_API_KEY || '');
  }

  async generateCompletion(options: LLMRequestOptions): Promise<string> {
    const model = this.ai.getGenerativeModel({
      model: this.modelName,
      generationConfig: { responseMimeType: 'application/json' },
      systemInstruction: options.systemPrompt,
    });

    const result = await model.generateContent(options.prompt);
    return result.response.text();
  }
}
