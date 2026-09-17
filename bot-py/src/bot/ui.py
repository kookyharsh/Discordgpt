
import discord


class ConfirmationView(discord.ui.View):
    def __init__(self, nonce: str, user_id: int, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.nonce = nonce
        self.user_id = user_id

    @discord.ui.button(label="Confirm & Execute", style=discord.ButtonStyle.danger, custom_id="confirm")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to confirm this action.", ephemeral=True)
            return

        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not authorized to cancel this action.", ephemeral=True)
            return

        embed = discord.Embed(
            title="❌ Action Cancelled",
            description="The confirmation request was cancelled by the user.",
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class DiscordUIComponents:
    @staticmethod
    def create_confirmation_embed(action_type: str, risk_level: str, plan_details: str, nonce: str) -> discord.Embed:
        color = discord.Color.red() if risk_level in ("HIGH", "CRITICAL") else discord.Color.gold()
        embed = discord.Embed(
            title=f"⚠️ Confirmation Required: {action_type}",
            description=f"The requested action involves potential server mutations.\n\n**Action Details:**\n```json\n{plan_details}\n```",
            color=color,
        )
        embed.add_field(name="Risk Level", value=risk_level, inline=True)
        embed.add_field(name="Expiration", value="5 minutes", inline=True)
        embed.set_footer(text=f"Action Nonce: {nonce}")
        return embed

    @staticmethod
    def create_success_embed(title: str, description: str) -> discord.Embed:
        return discord.Embed(title=f"✅ {title}", description=description, color=discord.Color.green())

    @staticmethod
    def create_error_embed(title: str, reason: str) -> discord.Embed:
        return discord.Embed(
            title=f"❌ {title}",
            description=f"**Reason:** {reason}\n\n*No changes were made.*",
            color=discord.Color.red(),
        )
