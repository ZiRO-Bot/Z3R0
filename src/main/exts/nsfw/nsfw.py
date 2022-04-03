"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import annotations

import aiohttp
import discord
from discord.ext import commands, menus

from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.errors import DefaultError, NotNSFWChannel
from ...core.menus import ZMenuView
from ...core.mixin import CogMixin
from ...utils.other import isNsfw


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
                    item.disabled = True  # type: ignore
                await self._message.edit(view=self)
            super().finalize(timedOut)
        except discord.HTTPException:
            pass

    @discord.ui.button(emoji="\N{BLACK SQUARE FOR STOP}")
    async def stopNeko(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.stop()

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}")
    async def getNewNeko(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = await self.getNeko(interaction)
        if interaction.message:
            return await interaction.message.edit(embed=e)


class NekoPageSource(menus.PageSource):
    def __init__(self, session, endpoint, onlyOne: bool = False):
        self.session = session or aiohttp.ClientSession()
        self.endpoint = endpoint
        self.onlyOne = onlyOne

    def is_paginating(self):
        return not self.onlyOne

    async def getNeko(self):
        for a in range(5):
            try:
                async with self.session.get(NEKO_API + self.endpoint) as req:
                    img = await req.json()
                    return (
                        ZEmbed()
                        .set_image(url=img["data"]["response"]["url"].replace(" ", "%20"))
                        .set_footer(text="Powered by nekos.life")
                    )
            except KeyError:
                continue
        raise DefaultError("Can't find any image, please try again later.")


DEFAULT_NEKO = "all_tags_ero"


class NSFW(commands.Cog, CogMixin):
    """NSFW Commands."""

    icon = "😳"

    def __init__(self, bot) -> None:
        super().__init__(bot)

    async def cog_check(self, ctx):
        """Only for NSFW channels"""
        if not isNsfw(ctx.channel):
            raise NotNSFWChannel
        return True

    @commands.command(
        aliases=(
            "pussy",
            "pantyhose",
            "tits",
            "boobs",
            "yuri",
            "cosplay",
            "futanari",
            "futa",
            "trap",
            "femdom",
            "anus",
        ),
        brief="Get hentai images from nekos.life",
        description=(
            "Get hentai images from nekos.life\n\n"
            "TIPS: Use different alias to get images from different hentai "
            "category"
        ),
    )
    async def hentai(self, ctx: Context):
        aliases = {"boobs": "tits", "futa": "futanari"}
        endpoints = {
            "any": DEFAULT_NEKO,
            "pussy": "pussy_lewd",
            "pantyhose": "pantyhose_lewd",
            "tits": "tits_lewd",
            "yuri": "yuri_lewd",
            "cosplay": "cosplay_lewd",
            "futanari": "futanari_lewd",
            "trap": "trap_lewd",
            "femdom": "femdom_lewd",
            "anus": "anus_lewd",
        }

        invokedWith = ctx.invoked_with or "any"

        value = aliases.get(invokedWith, invokedWith)

        menus = NekoMenu(
            ctx,
            NekoPageSource(
                self.bot.session,
                "/images/nsfw/img/" + endpoints.get(value, DEFAULT_NEKO),
            ),
        )
        await menus.start()
