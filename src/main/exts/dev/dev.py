"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import asyncio
import os
import time

import discord
from discord.app_commands import locale_str as _
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature

from ...core.bot import EXTS_DIR
from ...core.context import Context
from ...core.converter import BannedMember
from ...core.embed import ZEmbed
from ...core.menus import ZChoices, ZMenuPagesView, choice


# --- For reload all command status
OK = "<:ok:864033138832703498>"
ERR = "<:error:783265883228340245>"


class Developer(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """Debugging tools for bot devs."""

    icon = "<:verified_bot_developer:748090768237002792>"

    async def cog_check(self, ctx: Context):
        """Only bot master able to use debug cogs."""
        return self.bot.owner_ids and ctx.author.id in self.bot.owner_ids

    @Feature.Command(
        name="jishaku",
        aliases=("dev", "jsk"),
        invoke_without_command=True,
        ignore_extra=False,
    )
    async def jsk(self, ctx):
        await ctx.try_invoke("botinfo")

    async def tryLoadReload(self, extension: str):
        reloadFailMessage = "Failed to reload {}:"
        actionType = (
            "reload"
            if extension in self.bot.extensions or f"src.main.{EXTS_DIR}.{extension}" in self.bot.extensions
            else "load"
        )
        action = getattr(
            self.bot,
            f"{actionType}_extension",
        )
        try:
            try:
                await action(extension)
            except BaseException:
                await action(f"src.main.{EXTS_DIR}.{extension}")
        except Exception as exc:
            self.bot.logger.exception(reloadFailMessage.format(extension))
            raise exc

    @Feature.Command(parent="jsk", name="load", aliases=("reload",))
    async def jsk_load(self, ctx, *extensions):
        """Reload extension."""
        exts = extensions or self.bot.extensions.copy()
        status = {}
        for extension in exts:
            try:
                await self.tryLoadReload(extension)
            except BaseException:
                status[extension] = ERR
            else:
                status[extension] = OK

        e = ZEmbed.default(
            ctx,
        )

        if len(exts) > 1:
            e.title = "Extensions Load/Reload Status"
            e.description = "\n".join(["{} | `{}`".format(v, k) for k, v in status.items()])
        else:
            extension = exts[0]
            e.title = "{} | {} {}".format(
                status[extension],
                extension,
                "has been loaded/reloaded" if status[extension] == OK else "failed to load/reload",
            )

        return await ctx.tryReply(embed=e)

    @Feature.Command(parent="jsk", name="restart")
    async def jsk_restart(self, ctx):
        # NOTE: You'll need supervisor to use this
        await ctx.send("Restarting...")
        os.system("supervisorctl restart zibot &")

    @Feature.Command(parent="jsk", name="test_menu")
    async def jsk_test_menu(self, ctx):
        menu = ZMenuPagesView(ctx, ["1", "2"], timeout=5)
        await menu.start()

    @Feature.Command(parent="jsk", name="test_loading")
    async def jsk_test_loading(self, ctx):
        async with ctx.loading():
            await asyncio.sleep(5)
            await ctx.send(":D")

    @Feature.Command(parent="jsk", name="test_choices")
    async def jsk_test_choices(self, ctx):
        res = ZChoices(ctx, [choice("a", "aa"), choice("b", "bb")])
        await ctx.send(":)", view=res)
        await res.wait()
        await ctx.send(res.value)

    @Feature.Command(parent="jsk", name="news")
    async def jsk_news(self, ctx, *, news):
        """Set news"""
        ctx.bot.news["time"] = int(time.time())
        ctx.bot.news["content"] = news
        ctx.bot.news.dump()
        return await ctx.try_reply("News has been changed")

    @Feature.Command(parent="jsk", name="test_banned")
    async def jsk_get_banned(self, ctx, banned: BannedMember):
        """Testing BannedMember converter after Discord paginate ban list"""
        # TODO
        return await ctx.try_reply(banned.user.id)

    @Feature.Command(parent="jsk", name="i18n")
    async def jsk_i18n(self, ctx: Context):
        translated = await ctx.translate(_("var", name=ctx.author.name))
        msg = await ctx.try_reply(translated)
        translated2 = await ctx.translate(_("test"), locale=discord.Locale("id"))
        await msg.edit(content=msg.content + "\n" + translated2)

    @Feature.Command(parent="jsk", name="lang")
    async def jsk_lang(self, ctx: Context, language: str = "en-US"):
        ctx.bot.i18n.set(discord.Locale(language))
        await ctx.try_reply("Language has been changed")
