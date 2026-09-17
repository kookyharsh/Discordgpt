from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord


class ConfirmationView(discord.ui.View):
    def __init__(
        self,
        nonce: str,
        user_id: int,
        on_confirm: Callable[[discord.Interaction], Awaitable[None]] | None = None,
        timeout: float = 300.0,
    ):
        super().__init__(timeout=timeout)
        self.nonce = nonce
        self.user_id = user_id
        self._on_confirm = on_confirm

    @discord.ui.button(
        label="Confirm & Execute", style=discord.ButtonStyle.danger, custom_id="confirm"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You are not authorized to confirm this action.", ephemeral=True
            )
            return
        if self._on_confirm is not None:
            await self._on_confirm(interaction)
        else:
            await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You are not authorized to cancel this action.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="❌ Action Cancelled",
            description="The confirmation request was cancelled by the user.",
            color=discord.Color.red(),
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class DisambiguationView(discord.ui.View):
    def __init__(
        self,
        options: list[dict[str, str]],
        user_id: int,
        on_pick: Callable[[discord.Interaction, str], Awaitable[None]],
        timeout: float = 300.0,
    ):
        super().__init__(timeout=timeout)
        self._on_pick = on_pick
        self._user_id = user_id
        select = discord.ui.Select(
            placeholder="Pick one…",
            options=[
                discord.SelectOption(
                    label=o["name"][:100], value=o["id"], description=o["id"][:100]
                )
                for o in options[:10]
            ],
        )
        select.callback = self._selected  # type: ignore[method-assign]
        self.add_item(select)

    async def _selected(self, interaction: discord.Interaction):
        if interaction.user.id != self._user_id:
            await interaction.response.send_message("That menu isn't yours.", ephemeral=True)
            return
        chosen = interaction.data.get("values", [None])[0] if interaction.data else None
        await self._on_pick(interaction, chosen or "")
        self.stop()


class ClarifyModal(discord.ui.Modal):
    def __init__(
        self,
        title: str,
        on_submit_cb: Callable[[discord.Interaction, str], Awaitable[None]],
    ):
        super().__init__(title=title[:45])
        self._on_submit_cb = on_submit_cb
        self.answer = discord.ui.TextInput(
            label="Additional detail",
            placeholder="e.g. channel name, user, duration…",
            max_length=1000,
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        await self._on_submit_cb(interaction, str(self.answer.value or ""))


class DiscordUIComponents:
    @staticmethod
    def create_confirmation_embed(
        action_type: str, risk_level: str, plan_details: str, nonce: str
    ) -> discord.Embed:
        color = discord.Color.red() if risk_level in ("HIGH", "CRITICAL") else discord.Color.gold()
        embed = discord.Embed(
            title=f"⚠️ Confirmation Required: {action_type}",
            description=(
                "This action needs approval before anything changes.\n\n"
                f"**Details:**\n```json\n{plan_details[:1500]}\n```"
            ),
            color=color,
        )
        embed.add_field(name="Risk Level", value=risk_level, inline=True)
        embed.add_field(name="Expiration", value="5 minutes", inline=True)
        embed.set_footer(text=f"Action Nonce: {nonce}")
        return embed

    @staticmethod
    def create_question_embed(question: str) -> discord.Embed:
        return discord.Embed(
            title="❓ Clarification Needed",
            description=f"{question}\n\nPress **Answer** and provide the missing detail.",
            color=discord.Color.gold(),
        )

    @staticmethod
    def create_disambiguation_embed(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=f"🔀 {title}", description=description, color=discord.Color.blurple()
        )

    @staticmethod
    def create_success_embed(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=f"✅ {title}", description=description, color=discord.Color.green()
        )

    @staticmethod
    def create_error_embed(title: str, reason: str, hint: str | None = None) -> discord.Embed:
        description = f"**Reason:** {reason}\n\n*No changes were made.*"
        if hint:
            description += f"\n\n**Try this:** {hint}"
        return discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red(),
        )
