export class InjectionDefense {
  private static DANGEROUS_SYSTEM_PATTERNS = [
    /ignore (?:all|previous|\s)+ (?:instructions|directives)/i,
    /you are now in (?:developer|dan|admin) mode/i,
    /grant (?:me|yourself) administrator/i,
    /system prompt/i,
    /eval\s*\(/i,
    /child_process/i,
    /exec\s*\(/i,
  ];

  static sanitizeExternalText(text: string): string {
    return text.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').trim();
  }

  static detectPromptInjection(prompt: string): boolean {
    return this.DANGEROUS_SYSTEM_PATTERNS.some((pattern) => pattern.test(prompt));
  }
}
