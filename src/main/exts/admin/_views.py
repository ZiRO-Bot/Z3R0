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


class Greeting(discord.ui.Modal, title="Greeting"):
    message = discord.ui.TextInput(
        label="Message", placeholder="Welcome, {user(mention)}! {react: 👋}", style=discord.TextStyle.paragraph
    )

    # TODO - hopefully discord will add channel input soon into modal
    #        for now i'll comment this
    # channel = discord.ui.TextInput(
    #     label="Channel",
    #     placeholder="336642139381301249",
    # )

    def __init__(
        self,
        context: Context,
        type: str,
        *,
        defaultMessage: str | None = None,
    ) -> None:
        super().__init__(title=type.title())
        self.context = context
        self.type = type
        self.message.default = defaultMessage

    async def callback(self):
        await _common.handleGreetingConfig(self.context, self.type, message=self.message)  # type: ignore

    async def on_submit(self, inter: discord.Interaction):
        await self.callback()
        return await inter.response.defer()


class OpenGreetingModal(ZView):
    def __init__(self, context: Context, type, defaultMessage, message: discord.Message | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.context = context
        self.message = message
        self.type = type
        self.defaultMessage = defaultMessage

    async def on_timeout(self) -> None:
        if not self.message:
            return

        for item in self.children:
            if isinstance(item, discord.Button):
                item.disabled = True

        await self.message.edit(view=self)

    @discord.ui.button(label='Configure')
    async def configureGreeting(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = Greeting(self.context, self.type, defaultMessage=self.defaultMessage)
        await interaction.response.send_modal(modal)

        if not self.message:
            return

        button.disabled = True
        await self.message.edit(view=self)
