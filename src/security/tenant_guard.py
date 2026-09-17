class TenantGuard:
    @staticmethod
    def validate_guild_boundary(current_guild_id: str, target_guild_id: str) -> None:
        if current_guild_id != target_guild_id:
            raise ValueError(
                f"Tenant Isolation Violation: Cross-guild action detected ({current_guild_id} vs {target_guild_id})."
            )

    @staticmethod
    def validate_entity_guild(
        entity_guild_id: str, current_guild_id: str, entity_name: str
    ) -> None:
        if entity_guild_id != current_guild_id:
            raise ValueError(
                f"Tenant Isolation Violation: {entity_name} belongs to a different guild."
            )
