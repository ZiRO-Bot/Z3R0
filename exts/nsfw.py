"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import aiohttp
import discord
from discord.ext import commands, menus

from core.mixin import CogMixin
from exts.utils.format import ZEmbed

NEKO_API = "https://api.nekos.dev/api/v3"


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

    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == "REACTION_ADD":
                channel = self.bot.get_channel(payload.channel_id)
                msg = channel.get_partial_message(payload.message_id)
                await msg.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == "REACTION_REMOVE":
                return
        await super().update(payload)

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f", position=menus.First(0))
    async def stopNeko(self, payload):
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f", position=menus.First(1))
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
            NekoPageSource(self.bot.session, "/images/nsfw/img/pussy_lewd")
        )
        await menus.start(ctx)

    @commands.command()
    async def pantyhose(self, ctx):
        menus = NekoMenu(
            NekoPageSource(self.bot.session, "/images/nsfw/img/pantyhose_lewd")
        )
        await menus.start(ctx)

    @commands.command(aliases=("boobs",))
    async def tits(self, ctx):
        menus = NekoMenu(NekoPageSource(self.bot.session, "/images/nsfw/img/tits_lewd"))
        await menus.start(ctx)

    @commands.command()
    async def yuri(self, ctx):
        menus = NekoMenu(NekoPageSource(self.bot.session, "/images/nsfw/img/yuri_lewd"))
        await menus.start(ctx)

    @commands.command()
    async def cosplay(self, ctx):
        menus = NekoMenu(
            NekoPageSource(self.bot.session, "/images/nsfw/img/cosplay_lewd")
        )
        await menus.start(ctx)


def setup(bot):
    bot.add_cog(NSFW(bot))
