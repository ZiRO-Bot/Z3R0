"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import aiohttp
import discord
from discord.ext import commands, menus

from core.embed import ZEmbed
from core.menus import ZMenuView
from core.mixin import CogMixin


NEKO_API = "https://api.nekos.dev/api/v3"


class NekoMenu(ZMenuView):
    def __init__(self, ctx, source, **kwargs):
        self._source = source
        super().__init__(ctx, **kwargs)

    @property
    def source(self):
        return self._source

    def shouldAddButtons(self):
        return self._source.is_paginating()

    async def getNeko(self, interaction: discord.Interaction = None):
        if interaction:
            await interaction.response.defer()
        page = await self._source.getNeko()
        return page

    async def sendInitialMessage(self, ctx):
        e = await self.getNeko()
        return await ctx.send(embed=e, view=self)

    async def finalize(self, timedOut):
        try:
            if self._message:
                for item in self.children:
                    item.disabled = True
                await self._message.edit(view=self)
            super().finalize(timedOut)
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="\N{BLACK SQUARE FOR STOP}")
    async def stopNeko(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.stop()

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}")
    async def getNewNeko(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        e = await self.getNeko(interaction)
        await interaction.message.edit(embed=e)


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
            return (
                ZEmbed()
                .set_image(url=img["data"]["response"]["url"].replace(" ", "%20"))
                .set_footer(text="Powered by nekos.life")
            )


class NSFW(commands.Cog, CogMixin):
    """NSFW Commands."""

    icon = "😳"

    async def cog_check(self, ctx):
        """Only for NSFW channels"""
        if not ctx.guild:
            return True
        return ctx.channel.is_nsfw()

    @commands.command()
    async def pussy(self, ctx):
        menus = NekoMenu(
            ctx, NekoPageSource(self.bot.session, "/images/nsfw/img/pussy_lewd")
        )
        await menus.start()

    @commands.command()
    async def pantyhose(self, ctx):
        menus = NekoMenu(
            ctx, NekoPageSource(self.bot.session, "/images/nsfw/img/pantyhose_lewd")
        )
        await menus.start()

    @commands.command(aliases=("boobs",))
    async def tits(self, ctx):
        menus = NekoMenu(
            ctx, NekoPageSource(self.bot.session, "/images/nsfw/img/tits_lewd")
        )
        await menus.start()

    @commands.command()
    async def yuri(self, ctx):
        menus = NekoMenu(
            ctx, NekoPageSource(self.bot.session, "/images/nsfw/img/yuri_lewd")
        )
        await menus.start()

    @commands.command()
    async def cosplay(self, ctx):
        menus = NekoMenu(
            ctx, NekoPageSource(self.bot.session, "/images/nsfw/img/cosplay_lewd")
        )
        await menus.start()
