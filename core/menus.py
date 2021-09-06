from __future__ import annotations

import asyncio
from collections import namedtuple
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Union

import discord
from discord.ext import menus

from core.enums import Emojis
from core.views import ZView


if TYPE_CHECKING:
    from core.context import Context


class ZMenu(menus.MenuPages):
    def __init__(self, source, init_msg=None, check_embeds=True, ping=False, loop=None):
        super().__init__(source=source, check_embeds=check_embeds)
        self.ping = ping
        self.init_msg = init_msg

    async def start(self, ctx):
        await super().start(ctx)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if self.init_msg:
            await self.init_msg.edit(**kwargs)
            return self.init_msg
        else:
            self.init_msg = await ctx.channel.send(**kwargs)
            return self.init_msg

    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == "REACTION_ADD":
                channel = self.bot.get_channel(payload.channel_id)
                msg = channel.get_partial_message(payload.message_id)
                await msg.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == "REACTION_REMOVE":
                return
        await super().update(payload)

    async def finalize(self, timed_out):
        try:
            await self.message.clear_reactions()
        except discord.HTTPException:
            pass


class ZReplyMenu(ZMenu):
    def __init__(self, source, ping=False) -> None:
        self.ping = ping or False
        super().__init__(source=source, check_embeds=True)

    async def start(self, ctx):
        await super().start(ctx)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if self.init_msg:
            await self.init_msg.edit(**kwargs)
            return self.init_msg
        else:
            # e = discord.Embed(title="Loading...", colour=discord.Colour.blue())
            kwargs.update({"mention_author": self.ping})
            self.init_msg = await ctx.try_reply(**kwargs)
            return self.init_msg


Pages = List[Union[str, dict, discord.Embed]]


class ZMenuView(ZView):
    """Base class for View-based menus"""

    def __init__(
        self,
        ctx: Context,
        *,
        timeout: float = 180.0,
        ownerOnly: bool = True,
    ) -> None:
        owner: Union[discord.User, discord.Member] = ctx.author
        super().__init__(owner, timeout=timeout)
        self.context = ctx
        self._message: Optional[discord.Message] = None
        self.currentPage: int = 0
        if isinstance(owner, discord.Member):
            self.compact = owner.is_on_mobile()
        else:
            self.compact = False

    def shouldAddButtons(self):
        return True

    async def sendInitialMessage(self, ctx):
        raise NotImplementedError

    async def sendPage(self, interaction: discord.Interaction, pageNumber):
        raise NotImplementedError

    async def start(self):
        self._message = await self.sendInitialMessage(self.context)
        if not self.shouldAddButtons():
            super().stop()

    def finalize(self, timedOut: bool):
        super().stop()

    async def stop(self):
        await discord.utils.maybe_coroutine(self.finalize, False)

    async def on_timeout(self):
        await discord.utils.maybe_coroutine(self.finalize, True)


class ZMenuPagesView(ZMenuView):
    """Menus made out of Discord "View" components

    Accept list of str, dict, or discord.Embed

    Also accepts menus.PageSource for compatibility
    """

    def __init__(
        self,
        ctx: Context,
        source: Union[menus.PageSource, Pages],
        **kwargs,
    ) -> None:
        self._source: Union[menus.PageSource, Pages] = source
        super().__init__(ctx, **kwargs)
        self.pageFmt = ("Page " if not self.compact else "") + "{current}/{last}"
        self._pageInfo.label = self.pageFmt.format(current="N/A", last="N/A")

    def shouldAddButtons(self):
        source = self._source
        return len(source) > 1 if isinstance(source, list) else source.is_paginating()

    def getMaxPages(self):
        source = self._source
        return len(source) if isinstance(source, list) else source.get_max_pages()

    async def getKwargsFromPage(self, page) -> dict:
        source = self._source
        if isinstance(source, list):
            value = source[page]
        else:
            value = await discord.utils.maybe_coroutine(source.format_page, self, page)

        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"embed": value, "content": None}
        return {}

    async def getPage(self, pageNumber):
        source = self._source
        if isinstance(source, list):
            page = pageNumber
        else:
            page = await source.get_page(pageNumber)

        return await self.getKwargsFromPage(page)

    async def sendInitialMessage(self, ctx):
        kwargs = await self.getPage(0)
        if self.shouldAddButtons():
            kwargs["view"] = self
            self._pageInfo.label = self.pageFmt.format(
                current="1", last=self.getMaxPages()
            )
            if self.getMaxPages() == 2:
                self.remove_item(self._first)  # type: ignore
                self.remove_item(self._last)  # type: ignore
        return await ctx.try_reply(**kwargs)

    async def sendPage(
        self, interaction: discord.Interaction, pageNumber, doDefer: bool = True
    ):
        if doDefer:
            await interaction.response.defer()

        self.currentPage = pageNumber
        kwargs = await self.getPage(pageNumber)
        self._pageInfo.label = self.pageFmt.format(
            current=pageNumber + 1, last=self.getMaxPages()
        )
        await interaction.message.edit(view=self, **kwargs)  # type: ignore

    async def sendCheckedPage(self, interaction: discord.Interaction, pageNumber):
        maxPages = self.getMaxPages()
        try:
            if maxPages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.sendPage(interaction, pageNumber)
            elif maxPages > pageNumber >= 0:
                await self.sendPage(interaction, pageNumber)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def finalize(self, timedOut: bool):
        if self._message:
            await self._message.edit(view=None)
        super().finalize(timedOut)

    @discord.ui.button(
        emoji=Emojis.first,
    )
    async def _first(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.sendPage(interaction, 0)

    @discord.ui.button(
        emoji=Emojis.back,
    )
    async def _back(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.sendCheckedPage(interaction, self.currentPage - 1)

    @discord.ui.button(
        label="Page NaN/NaN",
        style=discord.ButtonStyle.blurple,
    )
    async def _pageInfo(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            content=(
                "{}, which page would you like to jump to? "
                "(within `1` to `{}`)".format(
                    self.context.author.mention, self.getMaxPages()
                )
            ),
            ephemeral=True,
        )

        with suppress(asyncio.TimeoutError):
            message: discord.Message = await self.context.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda msg: msg.author.id == interaction.user.id  # type: ignore
                and msg.channel.id == interaction.channel.id  # type: ignore
                and msg.content.isdigit(),
            )
            with suppress(discord.HTTPException, discord.NotFound):
                await message.delete()

            pageNumber = min(self.getMaxPages(), max(1, int(message.content))) - 1
            await self.sendPage(interaction, pageNumber, doDefer=False)

    @discord.ui.button(
        emoji=Emojis.next,
    )
    async def _forward(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.sendCheckedPage(interaction, self.currentPage + 1)

    @discord.ui.button(
        emoji=Emojis.last,
    )
    async def _last(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.sendPage(interaction, self.getMaxPages() - 1)

    @discord.ui.button(
        label="Stop paginator",
        emoji=Emojis.stop,
        style=discord.ButtonStyle.red,
    )
    async def _stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.stop()


choice = namedtuple("choice", ("label", "value"))


class ZChoices(ZView):
    """Basically send choices as buttons"""

    def __init__(self, ctx: Context, choices: Iterable[Any]):
        super().__init__(owner=ctx.author)
        self.context = ctx
        self.choices: Iterable[Any] = choices
        self.value: Any = None

        def makeCallback(choice):
            async def callback(interaction):
                await interaction.response.defer()
                self.value = choice.value
                self.stop()

            return callback

        for choice in self.choices:
            button = discord.ui.Button(label=choice.label)
            button.callback = makeCallback(choice)
            self.add_item(button)

    async def wait(self):
        await super().wait()

    async def start(self):
        await self.wait()
