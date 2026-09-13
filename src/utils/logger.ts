import pino from 'pino';
import { config } from '../config/index.js';

const isDev = config.NODE_ENV === 'development';

// Console keeps the configured level; the file always captures debug+
// so `logs/bot.log` has the full backend story (LLM payloads, timings).
// `logs` is gitignored. Tail live with: Get-Content logs/bot.log -Tail 50 -Wait
export const logger = pino({
  level: 'debug',
  transport: {
    targets: [
      isDev
        ? {
            target: 'pino-pretty',
            options: { colorize: true, translateTime: 'HH:MM:ss' },
            level: config.LOG_LEVEL,
          }
        : {
            target: 'pino/file',
            options: { destination: 1 },
            level: config.LOG_LEVEL,
          },
      {
        target: 'pino/file',
        options: { destination: './logs/bot.log', mkdir: true },
        level: 'debug',
      },
    ],
  },
});
