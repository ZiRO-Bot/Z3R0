from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ..utils.cache import CacheListFull, CacheUniqueViolation
from ..utils.format import cleanifyPrefix, formatCmdName
from . import db


if TYPE_CHECKING:
    from .bot import ziBot


class MonkeyPatch:
    def __init__(self, bot: ziBot):
        self.bot = bot

    def inject(self) -> None:
        """Inject some function to discord.py objects

        Maybe cursed for some python devs, but I miss Kotlin's "Extension
        Method" so deal with it :)
        """

        # --- discord.Guild.getPrefixes()
        def getPrefix(bot: ziBot):
            async def predicate(self: discord.Guild) -> list[str]:
                if bot.cache.prefixes.get(self.id) is None:  # type: ignore
                    # Only executed when there's no cache for guild's prefix
                    dbPrefixes = await db.Prefixes.filter(guild_id=self.id)

                    try:
                        bot.cache.prefixes.extend(self.id, [p.prefix for p in dbPrefixes])  # type: ignore
                    except ValueError:
                        return []

                return bot.cache.prefixes[self.id]  # type: ignore

            return predicate

        discord.Guild.getPrefixes = getPrefix(self.bot)

        # --- discord.Guild.getFormattedPrefixes()
        def formattedPrefixes(bot: ziBot):
            async def predicate(self: discord.Guild):
                _prefixes = await self.getPrefixes()
                prefixes = []
                for pref in _prefixes:
                    if pref.strip() == "`":
                        prefixes.append(f"`` {pref} ``")
                    elif pref.strip() == "``":
                        prefixes.append(f"` {pref} `")
                    else:
                        prefixes.append(f"`{pref}`")
                prefixes = ", ".join(prefixes)

                result = "My default prefixes are `{}` or {}".format(bot.defPrefix, bot.user.mention)  # type: ignore
                if prefixes:
                    result += "\n\nCustom prefixes: {}".format(prefixes)
                return result

            return predicate

        discord.Guild.getFormattedPrefixes = formattedPrefixes(self.bot)

        # --- discord.Guild.addPrefix(prefix: str)
        def addPrefix(bot: ziBot):
            async def predicate(self: discord.Guild, prefix: str) -> str:
                """Add a prefix"""
                # Making sure guild's prefixes being cached
                await self.getPrefixes()

                try:
                    bot.cache.prefixes.add(self.id, prefix)  # type: ignore
                except CacheUniqueViolation:
                    raise commands.BadArgument("Prefix `{}` is already exists".format(cleanifyPrefix(self, prefix)))
                except CacheListFull:
                    raise IndexError(
                        "Custom prefixes is full! (Only allowed to add up to `{}` prefixes)".format(
                            bot.cache.prefixes.limit  # type: ignore
                        )
                    )

                await db.Prefixes.create(prefix=prefix, guild_id=self.id)

                return prefix

            return predicate

        discord.Guild.addPrefix = addPrefix(self.bot)

        # --- discord.Guild.rmPrefix(prefix: str)
        def rmPrefix(bot: ziBot):
            async def predicate(self: discord.Guild, prefix: str) -> str:
                """Remove a prefix"""
                # Making sure guild's prefixes being cached
                await self.getPrefixes()

                try:
                    bot.cache.prefixes.remove(self.id, prefix)  # type: ignore
                except IndexError:
                    raise commands.BadArgument("Prefix `{}` is not exists".format(cleanifyPrefix(self, prefix)))

                [await i.delete() for i in await db.Prefixes.filter(prefix=prefix, guild_id=self.id)]

                return prefix

            return predicate

        discord.Guild.rmPrefix = rmPrefix(self.bot)
