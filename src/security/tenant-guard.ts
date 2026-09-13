export class TenantGuard {
  public static validateGuildScope(interactionGuildId: string, targetGuildId: string): void {
    if (interactionGuildId !== targetGuildId) {
      throw new Error(`CrossGuildSecurityError: Target guild ${targetGuildId} does not match interaction guild ${interactionGuildId}.`);
    }
  }

  public static sanitizeEntityId(id: string): string {
    if (!/^\d{17,20}$/.test(id) && !/^chan-|^role-|^user-/.test(id)) {
      throw new Error(`InvalidEntityIdError: Provided ID '${id}' is malformed or untrusted.`);
    }
    return id;
  }
}
