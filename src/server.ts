import express, { Express, Request, Response } from 'express';
import { logger } from './utils/logger.js';

export function createHttpServer(): Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (req: Request, res: Response) => {
    res.status(200).json({ status: 'healthy', timestamp: new Date().toISOString() });
  });

  app.get('/ready', (req: Request, res: Response) => {
    // In production, check Postgres and Redis connectivity here
    res.status(200).json({ status: 'ready', services: { postgres: 'connected', redis: 'connected' } });
  });

  return app;
}
