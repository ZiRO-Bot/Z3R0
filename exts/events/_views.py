import discord


class Report(discord.ui.View):
    def __init__(self, user, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.user = user
        self.value = False

    async def interaction_check(self, interaction):
        owner = self.user
        if interaction.user.id != owner.id:
            await interaction.response.send_message(
                f"This interaction belongs to {owner.mention}", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Report Error", style=discord.ButtonStyle.red)
    async def report(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Reporting...", ephemeral=True)
        self.value = True
        self.stop()
