"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import io
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Union, overload

import aiohttp
import discord
from discord import Locale, Message
from discord.app_commands import locale_str as _
from discord.ext import commands
from discord.utils import MISSING

from .embed import ZEmbed, ZEmbedBuilder
from .guild import GuildWrapper


if TYPE_CHECKING:
    from .bot import ziBot

    LocaleStr = _


class Context(commands.Context):
    if TYPE_CHECKING:
        bot: ziBot

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @property
    def cache(self):
        return self.bot.cache

    @overload
    async def maybeTranslate(self, content: LocaleStr | None, fallback: None = ...) -> None:
        ...

    @overload
    async def maybeTranslate(self, content: LocaleStr | None, fallback: str = ...) -> str:
        ...

    @overload
    async def maybeTranslate(self, content: LocaleStr | str) -> str:
        ...

    @overload
    async def maybeTranslate(self, content: LocaleStr | str | None, fallback: None = ...) -> None:
        ...

    @overload
    async def maybeTranslate(self, content: LocaleStr | str | None, fallback: str = ...) -> str:
        ...

    async def maybeTranslate(self, content: LocaleStr | str | None, fallback: str | None = None) -> str | None:
        if not content:
            return content or fallback

        if isinstance(content, LocaleStr):
            content = await self.translate(content)
        return content

    async def send(self, content: LocaleStr | str | None = None, **kwargs) -> Message:
        return await super().send(await self.maybeTranslate(content), **kwargs)

    async def reply(self, content: LocaleStr | str | None = None, **kwargs) -> Message:
        return await super().reply(await self.maybeTranslate(content), **kwargs)

    async def tryReply(
        self,
        content: LocaleStr | str | None = None,
        *,
        mention_author=False,
        embed: discord.Embed | ZEmbedBuilder | None = None,
        embeds: list[discord.Embed | ZEmbedBuilder] = [],
        **kwargs,
    ):
        """Try reply, if failed do send instead"""
        if isinstance(embed, ZEmbedBuilder):
            embed = await embed.build(self)

        _embeds: list[discord.Embed] = []
        if embeds:
            for embed in embeds:
                if isinstance(embed, ZEmbedBuilder):
                    embed = await embed.build(self)
                _embeds.append(embed)

        if embed:
            kwargs["embed"] = embed
        if _embeds:
            kwargs["embeds"] = _embeds

        if self.interaction is None or self.interaction.is_expired():
            try:
                action = self.safeReply
                return await action(content, mention_author=mention_author, **kwargs)
            except BaseException:
                content = await self.maybeTranslate(content, "")

                if mention_author:
                    content = f"TAG: {self.author.mention}\n\n" + content

                action = self.safeSend
                return await action(content, **kwargs)

        return await self.send(content, **kwargs)

    try_reply = tryReply  # Deprecate

    async def safe_send_reply(self, content, *, escape_mentions=True, type="send", **kwargs):
        action = getattr(self, type)

        if escape_mentions and content is not None:
            content = discord.utils.escape_mentions(content)

        if content is not None and len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop("file", None)
            return await action(file=discord.File(fp, filename="message_too_long.txt"), **kwargs)
        else:
            if content is not None:
                kwargs["content"] = content
            return await action(**kwargs)

    async def safe_send(self, content, *, escape_mentions: bool = True, **kwargs):
        # TODO: Deprecate
        return await self.safe_send_reply(content, escape_mentions=escape_mentions, type="send", **kwargs)

    async def safeSend(self, content, *, escapeMentions: bool = True, **kwargs):
        return await self.safe_send(content, escape_mentions=escapeMentions, **kwargs)

    async def safe_reply(self, content, *, escape_mentions: bool = True, **kwargs):
        # TODO: Deprecate
        return await self.safe_send_reply(content, escape_mentions=escape_mentions, type="reply", **kwargs)

    async def safeReply(self, content, *, escapeMentions: bool = True, **kwargs):
        return await self.safe_reply(content, escape_mentions=escapeMentions, **kwargs)

    async def error(self, errorMessage: LocaleStr | str | None = None, title: LocaleStr | str | None = _("error-generic")):
        if isinstance(title, str):
            title = "ERROR: " + title
        else:
            title = await self.maybeTranslate(title, "")

        e = ZEmbed.error(title=title)
        if errorMessage is not None:
            e.description = await self.maybeTranslate(errorMessage, fallback="")
        return await self.try_reply(embed=e)

    async def success(self, success_message: LocaleStr | str | None = None, title: LocaleStr | str = _("success")):
        e = ZEmbed.success(
            title=await self.maybeTranslate(title),
        )
        if success_message is not None:
            e.description = str(success_message)
        return await self.try_reply(embed=e)

    @asynccontextmanager
    async def loading(self, title: LocaleStr | str = _("loading"), *, colour: discord.Colour | int = None):
        """
        async with ctx.loading(title="This param is optional"):
            await asyncio.sleep(5) # or any long process stuff
            await ctx.send("Finished")
        """
        if self.interaction:
            yield await self.interaction.response.defer()
            return

        e = ZEmbed.loading(title=await self.maybeTranslate(title), colour=colour)
        msg = None
        try:
            msg = await self.try_reply(embed=e)
            yield msg
        finally:
            if msg:
                await msg.delete()

    async def try_invoke(self, command: Union[commands.Command, str], *args, **kwargs):  # type: ignore
        """Similar to invoke() except it triggers checks"""
        if isinstance(command, str):
            command: commands.Command | None = self.bot.get_command(command)
            if not command:
                return

        canRun = await command.can_run(self)
        if canRun:
            await command(self, *args, **kwargs)  # type: ignore

    @discord.utils.cached_property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @discord.utils.cached_property
    def guild(self) -> GuildWrapper | None:
        g = self.message.guild
        if g:
            return GuildWrapper(g, self.bot)
        return None

    def requireGuild(self) -> GuildWrapper:
        """
        Inspired by Android's requireActivity()

        Should only be used if the command has guild only check
        """
        g = self.guild
        if not g:
            raise commands.NoPrivateMessage
        return g

    async def translate(self, string: LocaleStr, *, locale: Locale | None = None) -> str:
        """|coro|

        Mimic Interaction.translate() behaviour
        """
        if self.interaction:
            return await self.interaction.translate(string, locale=locale or MISSING) or string.message
        return await self.bot.i18n.format(string, locale=locale)
