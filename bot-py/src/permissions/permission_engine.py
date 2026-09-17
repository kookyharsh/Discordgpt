import discord


class PermissionEngine:
    @staticmethod
    def check_bot_permissions(guild: discord.Guild, required_permissions: discord.Permissions) -> tuple[bool, list[str]]:
        bot_member = guild.me
        if not bot_member:
            return False, ["Bot member not present in guild context"]

        missing: list[str] = []
        for perm, value in required_permissions:
            if value and not getattr(bot_member.permissions, perm, False):
                missing.append(perm.upper())

        if missing:
            return False, missing
        return True, []

    @staticmethod
    def check_user_permissions(member: discord.Member, required_permissions: discord.Permissions) -> tuple[bool, list[str]]:
        missing: list[str] = []
        for perm, value in required_permissions:
            if value and not getattr(member.permissions, perm, False):
                missing.append(perm.upper())

        if missing:
            return False, missing
        return True, []

class HierarchyEngine:
    @staticmethod
    def can_actor_manage_member(actor: discord.Member, target: discord.Member) -> bool:
        if actor.guild.owner_id == actor.id:
            return True
        if target.guild.owner_id == target.id:
            return False
        return actor.top_role.position > target.top_role.position

    @staticmethod
    def can_actor_manage_role(actor: discord.Member, target_role: discord.Role) -> bool:
        if actor.guild.owner_id == actor.id:
            return True
        if target_role.is_integration():
            return False
        return actor.top_role.position > target_role.position

    @staticmethod
    def can_bot_manage_role(guild: discord.Guild, target_role: discord.Role) -> tuple[bool, str | None]:
        bot_member = guild.me
        if not bot_member:
            return False, "Bot member object missing in guild context."

        if target_role.is_integration():
            return False, f"Role @{target_role.name} is managed by an integration."

        if bot_member.top_role.position <= target_role.position:
            return False, f"Role @{target_role.name} (pos {target_role.position}) is higher than or equal to bot top role (pos {bot_member.top_role.position})."

        return True, None

    @staticmethod
    def can_bot_manage_member(guild: discord.Guild, target_member: discord.Member) -> tuple[bool, str | None]:
        bot_member = guild.me
        if not bot_member:
            return False, "Bot member object missing in guild context."

        if guild.owner_id == target_member.id:
            return False, "Bot cannot execute administrative operations against the Guild Owner."

        if bot_member.top_role.position <= target_member.top_role.position:
            return False, f"Target user {target_member} has a role equal to or higher than the bot's top role."

        return True, None
