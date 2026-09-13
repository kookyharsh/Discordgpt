export class PromptInjectionDefense {
  private static readonly INJECTION_PATTERNS = [
    /ignore (all )?previous instructions/i,
    /system prompt/i,
    /you are now/i,
    /give (me|yourself) admin/i,
    /bypass permission/i,
    /eval\s*\(/i,
    /child_process/i,
    /execSync/i,
  ];

  public static sanitizeInput(input: string): string {
    // Strip control characters while preserving utf-8 natural text
    return input.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g, '').trim();
  }

  public static detectInjectionAttempt(input: string): boolean {
    return this.INJECTION_PATTERNS.some((pattern) => pattern.test(input));
  }
}
