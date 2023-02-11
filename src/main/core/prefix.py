"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from tortoise.exceptions import IntegrityError

from ..utils.cache import CacheListFull, CacheUniqueViolation
from ..utils.format import cleanifyPrefix
from . import db


if TYPE_CHECKING:
    from .bot import ziBot


__all__ = ("Prefix",)


class Prefix:
    def __init__(self, *, owner: discord.Guild | discord.User, bot: ziBot):
        self.owner: discord.Guild | discord.User = owner
        self.bot: ziBot = bot

    async def fetch(self) -> list[db.Prefixes]:
        if self.owner is discord.Guild:
            return await db.Prefixes.filter(guild_id=self.owner.id)
        return []

    async def get(self) -> list[str]:
        if self.bot.cache.prefixes.get(self.owner.id) is None:  # type: ignore
            # Only executed when there's no cache for guild's prefix
            dbPrefixes = await self.fetch()

            try:
                self.bot.cache.prefixes.extend(self.owner.id, [p.prefix for p in dbPrefixes])  # type: ignore
            except ValueError:
                return []

        return self.bot.cache.prefixes[self.owner.id]  # type: ignore

    async def getFormatted(self) -> str:
        _prefixes = await self.get()
        prefixes = []
        for pref in _prefixes:
            if pref.strip() == "`":
                prefixes.append(f"`` {pref} ``")
            elif pref.strip() == "``":
                prefixes.append(f"` {pref} `")
            else:
                prefixes.append(f"`{pref}`")
        prefixes = ", ".join(prefixes)

        result = "My default prefixes are `{}` or {}".format(self.bot.defPrefix, self.bot.user.mention)  # type: ignore
        if prefixes:
            result += "\n\nCustom prefixes: {}".format(prefixes)
        return result

    async def add(self, prefix: str) -> str:
        prefixes = await self.fetch()

        try:
            if prefixes and (len(prefixes) + 1) > self.bot.cache.prefixes.limit:  # type: ignore
                raise CacheListFull

            self.bot.cache.prefixes.add(self.owner.id, prefix)  # type: ignore
            await db.Prefixes.create(prefix=prefix, guild_id=self.owner.id)
        except (CacheUniqueViolation, IntegrityError) as exc:
            if exc is IntegrityError:
                self.bot.cache.prefixes.remove(self.owner.id, prefix)  # type: ignore
            raise commands.BadArgument("Prefix `{}` is already exists".format(self.cleanify(prefix)))
        except CacheListFull:
            raise IndexError(
                "Custom prefixes is full! (Only allowed to add up to `{}` prefixes)".format(
                    self.bot.cache.prefixes.limit  # type: ignore
                )
            )

        return prefix

    async def remove(self, prefix: str) -> str:
        try:
            res = [await i.delete() for i in await db.Prefixes.filter(prefix=prefix, guild_id=self.owner.id)]
            if not res:
                raise IndexError

            self.bot.cache.prefixes.remove(self.owner.id, prefix)  # type: ignore
        except IndexError:
            raise commands.BadArgument("Prefix `{}` is not exists".format(self.cleanify(prefix)))

        return prefix

    def cleanify(self, prefix: str) -> str:
        return cleanifyPrefix(self.bot, prefix)
