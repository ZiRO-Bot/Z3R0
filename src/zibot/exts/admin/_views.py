"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import discord

from ...core.context import Context
from ...core.views import ZView
from . import _common


class Greeting(discord.ui.Modal):
    # TODO: Change this to Channel Select menu when discord finally added them
    # They really take their time for this one, even tho modal itself is pretty
    # rushed, I'm impressed Discord (NOT!)
    channel = discord.ui.TextInput(
        label="Channel",
        placeholder="You can type #channel-name or the channels' ID for better accuracy",
    )

    message = discord.ui.TextInput(
        label="Message", placeholder="Welcome, {user(mention)}! {react: 👋}", style=discord.TextStyle.paragraph
    )

    def __init__(
        self,
        context: Context,
        type: str,
    ) -> None:
        super().__init__(title=type.title())
        self.context = context
        self.type = type

    async def on_submit(self, inter: discord.Interaction):
        await _common.handleGreetingConfig(self.context, self.type, message=self.message.value)
        return await inter.response.defer()


class OpenGreetingModal(ZView):
    def __init__(self, context: Context, type, message: discord.Message | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.context = context
        self.message = message
        self.type = type

    async def on_timeout(self) -> None:
        if not self.message:
            return

        for item in self.children:
            if isinstance(item, discord.Button):
                item.disabled = True

        await self.message.edit(view=self)

    @discord.ui.button(label='Configure')
    async def configureGreeting(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = Greeting(self.context, self.type)
        await interaction.response.send_modal(modal)

        if not self.message:
            return

        self.configureGreeting.disabled = True
        await self.message.edit(view=self)
        self.message = None  # Clean up
