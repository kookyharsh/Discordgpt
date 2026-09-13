import dotenv from 'dotenv';
import { z } from 'zod';

dotenv.config();

const envSchema = z.object({
  DISCORD_TOKEN: z.string().default('mock_token'),
  DISCORD_CLIENT_ID: z.string().default('mock_client_id'),
  DISCORD_CLIENT_SECRET: z.string().optional(),
  DATABASE_URL: z.string().default('postgresql://postgres:postgres@localhost:5432/discordgpt?schema=public'),
  REDIS_URL: z.string().default('redis://localhost:6379'),
  LLM_PROVIDER: z.enum(['openai', 'gemini', 'claude', 'mock']).default('mock'),
  LLM_API_KEY: z.string().default('mock_key'),
  LLM_MODEL: z.string().default('gpt-4o'),
  OPENAI_API_KEY: z.string().optional(),
  GEMINI_API_KEY: z.string().optional(),
  ANTHROPIC_API_KEY: z.string().optional(),
  PORT: z.coerce.number().default(3000),
  LOG_LEVEL: z.enum(['trace', 'debug', 'info', 'warn', 'error', 'fatal']).default('info'),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
});

export const config = envSchema.parse(process.env);
export type Config = z.infer<typeof envSchema>;
