"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

import discord

from .prefix import Prefix


if TYPE_CHECKING:
    from .bot import ziBot


__all__ = ("GuildWrapper", "CCMode")


class CCMode(Enum):
    MOD_ONLY = 0
    PARTIAL = 1
    ANARCHY = 2

    def __str__(self):
        MODES = [
            "Only mods can add and manage custom commands",
            "Member can add custom command but can only manage **their own** commands",
            "**A N A R C H Y**",
        ]
        return MODES[self.value]


class GuildWrapper:
    """Wrapper for Guild class to get config from database easier"""

    def __init__(self, guild: discord.Guild, bot: ziBot):
        self.guild = guild
        self.bot = bot
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

    async def getConfig(self, configType: str) -> Any:
        # TODO: Move self.bot.getGuildConfig codes here
        return await self.bot.getGuildConfig(self.id, configType)

    async def getCCMode(self) -> CCMode:
        return CCMode(await self.bot.getGuildConfig(self.id, "ccMode") or 0)
