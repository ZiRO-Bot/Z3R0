import discord

from core.views import ZView


class Report(ZView):
    def __init__(self, user, timeout: float = 180.0):
        super().__init__(owner=user, timeout=timeout)
        self.value = False

    @discord.ui.button(label="Report Error", style=discord.ButtonStyle.red)
    async def report(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Reporting...", ephemeral=True)
        self.value = True
        self.stop()
