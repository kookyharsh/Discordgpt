import { describe, it, expect } from 'vitest';
import { summarizePlan, MAX_PLAN_STEPS } from './plan-executor.js';

describe('summarizePlan', () => {
  it('summarizes all-ok plans', () => {
    const text = summarizePlan([
      { stepId: '1', action: 'create_channel', ok: true },
      { stepId: '2', action: 'send_message', ok: true },
    ]);
    expect(text).toContain('2/2 steps succeeded');
    expect(text).toContain('✓ create_channel');
  });

  it('summarizes partial failures', () => {
    const text = summarizePlan([
      { stepId: '1', action: 'create_channel', ok: true },
      { stepId: '2', action: 'ban_member', ok: false, error: 'Missing permissions' },
    ]);
    expect(text).toContain('1/2 steps succeeded');
    expect(text).toContain('✗ ban_member: Missing permissions');
  });

  it('handles empty results and caps plan size', () => {
    expect(summarizePlan([])).toContain('No steps');
    expect(MAX_PLAN_STEPS).toBeLessThanOrEqual(5);
  });
});
