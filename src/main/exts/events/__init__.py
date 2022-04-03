"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union

import discord
from discord.app_commands import AppCommandError, Command, ContextMenu

from .events import EventHandler


if TYPE_CHECKING:
    from ...core.bot import ziBot


async def setup(bot: ziBot):
    await bot.add_cog(EventHandler(bot))

    # TODO - Finish this handler
    @bot.tree.error
    async def app_command_error(
        interaction: discord.Interaction, command: Union[Command, ContextMenu], error: AppCommandError
    ):
        await interaction.response.send_message("hmm")
