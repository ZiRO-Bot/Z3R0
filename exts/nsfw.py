"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import aiohttp
import discord


from core.mixin import CogMixin
from discord.ext import commands, menus
from exts.utils.format import ZEmbed


NEKO_API = "https://nekos.life/api/v2"


class NekoMenu(menus.Menu):
    def __init__(self, source, **kwargs):
        self._source = source
        super().__init__(**kwargs)

    @property
    def source(self):
        return self._source

    async def getNeko(self):
        page = await self._source.getNeko()
        return page

    async def send_initial_message(self, ctx, channel):
        e = await self.getNeko()
        return await channel.send(embed=e)

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f', position=menus.First(0))
    async def stopNeko(self, payload):
        self.stop()

    @menus.button('\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f', position=menus.First(1))
    async def getNewNeko(self, payload):
        e = await self.getNeko()
        await self.message.edit(embed=e)

    async def finalize(self, timed_out):
        try:
            await self.message.clear_reactions()
        except discord.HTTPException:
            pass


class NekoPageSource(menus.PageSource):
    def __init__(self, session, endpoint, onlyOne: bool = False):
        self.session = session or aiohttp.ClientSession()
        self.endpoint = endpoint
        self.onlyOne = onlyOne

    def is_paginating(self):
        return not self.onlyOne

    async def getNeko(self):
        async with self.session.get(NEKO_API + self.endpoint) as req:
            img = await req.json()
            return ZEmbed().set_image(url=img["url"])


class NSFW(commands.Cog, CogMixin):
    """NSFW Commands."""

    icon = "😳"

    async def cog_check(self, ctx):
        """Only for NSFW channels"""
        return ctx.channel.is_nsfw()

    @commands.command()
    async def pussy(self, ctx):
        menus = NekoMenu(NekoPageSource(self.bot.session, "/img/pussy"))
        await menus.start(ctx)


def setup(bot):
    bot.add_cog(NSFW(bot))
