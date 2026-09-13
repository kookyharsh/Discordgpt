import Fastify from 'fastify';
import { prisma } from '../database/prisma.js';

export function createFastifyServer() {
  const fastify = Fastify({ logger: false });

  fastify.get('/health', async () => {
    return { status: 'ok', timestamp: new Date().toISOString() };
  });

  fastify.get('/ready', async (request, reply) => {
    try {
      await prisma.$queryRaw`SELECT 1`;
      return { status: 'ready', database: 'connected' };
    } catch (err: any) {
      reply.status(503);
      return { status: 'unready', database: err.message };
    }
  });

  fastify.get('/metrics', async () => {
    return {
      uptime: process.uptime(),
      memoryUsage: process.memoryUsage(),
    };
  });

  return fastify;
}
