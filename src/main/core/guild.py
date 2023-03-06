"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .prefix import Prefix


if TYPE_CHECKING:
    from .bot import ziBot


__all__ = ("GuildWrapper",)


class GuildWrapper:
    """Wrapper for Guild class to get config from database easier"""

    def __init__(self, guild: discord.Guild, bot: ziBot):
        self.guild = guild
        self.prefix = Prefix(owner=self.guild, bot=bot)

    @classmethod
    def fromContext(cls, guild: discord.Guild | None, bot: ziBot) -> GuildWrapper | None:
        if guild:
            return cls(guild, bot)
        return None

    def __str__(self) -> str:
        return str(self.guild)

    def __getattr__(self, name: str):
        try:
            return self.guild.__getattribute__(name)
        except:
            return self.__getattribute__(name)

    async def getPrefixes(self):
        return await self.prefix.get()

    async def getFormattedPrefixes(self):
        return await self.prefix.getFormatted()

    async def rmPrefix(self, prefix: str):
        return await self.prefix.remove(prefix)

    async def addPrefix(self, prefix: str):
        return await self.prefix.add(prefix)
