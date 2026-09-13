export class TenantGuard {
  static validateGuildBoundary(currentGuildId: string, targetGuildId: string): void {
    if (currentGuildId !== targetGuildId) {
      throw new Error(`Tenant Isolation Violation: Cross-guild action detected (${currentGuildId} vs ${targetGuildId}).`);
    }
  }

  static validateEntityGuild(entityGuildId: string, currentGuildId: string, entityName: string): void {
    if (entityGuildId !== currentGuildId) {
      throw new Error(`Tenant Isolation Violation: ${entityName} belongs to a different guild.`);
    }
  }
}
