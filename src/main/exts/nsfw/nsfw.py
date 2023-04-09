"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import typing
from typing import Literal

import aiohttp
import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.ext import commands, menus

from ...core.context import Context
from ...core.embed import ZEmbed
from ...core.errors import DefaultError, NotNSFWChannel
from ...core.menus import ZMenuView
from ...core.mixin import CogMixin
from ...utils import isNsfw


NEKO_API = "http://api.nekos.fun:8080/api/"


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
        for _ in range(5):
            try:
                async with self.session.get(NEKO_API + self.endpoint) as req:
                    img = await req.json()
                    return ZEmbed().set_image(url=img["image"].replace(" ", "%20")).set_footer(text="Powered by nekos.fun")
            except KeyError:
                continue
        raise DefaultError("Can't find any image, please try again later.")


DEFAULT_NEKO = "lewd"
TAGS = Literal[
    "pussy",
    "feet",
    "tits",
    "boobs",
    "yuri",
    "lesbian",
    "holo",
    "ahegao",
    "gasm",
    "ass",
]


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

    async def showHentai(self, ctx, tag: str):
        endpoints = {
            "any": DEFAULT_NEKO,
            "pussy": "pussy",
            "feet": "feet",
            "boobs": "boobs",
            "lesbian": "lesbian",
            "holo": "holo",
            "gasm": "gasm",
            "ass": "ass",
        }

        menus = NekoMenu(
            ctx,
            NekoPageSource(
                self.bot.session,
                endpoints.get(tag, DEFAULT_NEKO),
            ),
        )
        await menus.start()

    @app_commands.command(name=_("hentai"), nsfw=True, description=_("hentai-desc"))
    async def hentaiSlash(self, inter: discord.Interaction, tag: TAGS):
        ctx = await Context.from_interaction(inter)
        return await self.showHentai(ctx, tag)

    @commands.command(
        aliases=typing.get_args(TAGS),
        description="Get hentai images from nekos.fun",
        help="\n\nTIPS: Use different alias to get images from different hentai category",
    )
    async def hentai(self, ctx: Context):
        aliases = {"tits": "boobs", "yuri": "lesbian", "ahegao": "gasm"}
        invokedWith = ctx.invoked_with or "any"

        tag = aliases.get(invokedWith, invokedWith)
        return await self.showHentai(ctx, tag)
