import { LLMProvider, LLMRequestOptions } from '../types.js';

export class MockLLMProvider implements LLMProvider {
  name = 'mock';
  public mockResponses: Map<string | RegExp, string> = new Map();
  public defaultResponse: string = JSON.stringify({
    status: 'direct_action',
    intentType: 'single_action',
    action: 'get_server_info',
    parameters: {},
  });

  async generateCompletion(options: LLMRequestOptions): Promise<string> {
    for (const [pattern, resp] of this.mockResponses.entries()) {
      if (typeof pattern === 'string' && options.prompt.includes(pattern)) {
        return resp;
      }
      if (pattern instanceof RegExp && pattern.test(options.prompt)) {
        return resp;
      }
    }
    return this.defaultResponse;
  }
}
