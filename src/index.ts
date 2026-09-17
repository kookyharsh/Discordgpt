import { config } from './config/index.js';
import { logger } from './utils/logger.js';

logger.info({ env: config.NODE_ENV, port: config.PORT }, 'Starting Discord Natural Language Agent Service...');
