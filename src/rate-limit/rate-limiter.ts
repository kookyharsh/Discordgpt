import { Redis } from 'ioredis';

export interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

export class RateLimiter {
  private redisClient?: InstanceType<typeof Redis>;
  private memoryMap: Map<string, { count: number; resetAt: number }> = new Map();

  constructor(redisUrl?: string) {
    if (redisUrl && process.env.NODE_ENV !== 'test') {
      try {
        this.redisClient = new Redis(redisUrl, { maxRetriesPerRequest: null, lazyConnect: true });
      } catch (err) {
        // Fallback to memory limiter if Redis fails to connect
      }
    }
  }

  async isRateLimited(key: string, limit: number, windowSeconds: number): Promise<{ limited: boolean; remaining: number }> {
    if (this.redisClient && this.redisClient.status === 'ready') {
      try {
        const current = await this.redisClient.incr(key);
        if (current === 1) {
          await this.redisClient.expire(key, windowSeconds);
        }
        if (current > limit) {
          return { limited: true, remaining: 0 };
        }
        return { limited: false, remaining: limit - current };
      } catch (err) {
        // Fallback to in-memory check
      }
    }

    const now = Date.now();
    const entry = this.memoryMap.get(key);
    if (!entry || entry.resetAt <= now) {
      this.memoryMap.set(key, { count: 1, resetAt: now + windowSeconds * 1000 });
      return { limited: false, remaining: limit - 1 };
    }

    entry.count += 1;
    if (entry.count > limit) {
      return { limited: true, remaining: 0 };
    }
    return { limited: false, remaining: limit - entry.count };
  }
}
