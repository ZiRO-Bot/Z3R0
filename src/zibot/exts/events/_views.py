"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import discord

from ...core.views import ZView


class Report(ZView):
    def __init__(self, user, timeout: float = 180.0):
        super().__init__(owner=user, timeout=timeout)
        self.value = False

    @discord.ui.button(label="Report Error", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Reporting...", ephemeral=True)
        self.value = True
        self.stop()
