import { LLMProvider } from './types.js';
import { GeminiLLMProvider } from './gemini-provider.js';
import { OpenAILLMProvider } from './openai-provider.js';
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';

export function createLLMProvider(): LLMProvider {
  switch (config.LLM_PROVIDER) {
    case 'openrouter': {
      const apiKey = config.OPENROUTER_API_KEY || config.OPENAI_API_KEY;
      if (!apiKey) {
        logger.warn('No OPENROUTER_API_KEY or OPENAI_API_KEY found, falling back to mock / error state');
      }
      logger.info({ model: config.OPENROUTER_MODEL }, 'Using OpenRouter LLM Provider');
      return new OpenAILLMProvider({
        apiKey: apiKey || '',
        baseUrl: 'https://openrouter.ai/api/v1',
        model: config.OPENROUTER_MODEL,
        providerName: 'OpenRouter',
      });
    }
    case 'openai': {
      logger.info({ model: config.OPENAI_MODEL, baseUrl: config.OPENAI_BASE_URL }, 'Using OpenAI LLM Provider');
      return new OpenAILLMProvider({
        apiKey: config.OPENAI_API_KEY || '',
        baseUrl: config.OPENAI_BASE_URL,
        model: config.OPENAI_MODEL,
        providerName: 'OpenAI',
      });
    }
    case 'gemini':
    default: {
      logger.info({ model: config.GEMINI_MODEL }, 'Using Gemini LLM Provider');
      return new GeminiLLMProvider();
    }
  }
}
