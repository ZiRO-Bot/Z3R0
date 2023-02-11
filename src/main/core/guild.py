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

    def __getattr__(self, name: str):
        try:
            return self.guild.__getattribute__(name)
        except:
            return self.__getattribute__(name)

    def getPrefixes(self):
        return self.prefix.get()

    def getFormattedPrefixes(self):
        return self.prefix.getFormatted()

    def rmPrefix(self, prefix: str):
        return self.prefix.remove(prefix)

    def addPrefix(self, prefix: str):
        return self.prefix.add(prefix)
