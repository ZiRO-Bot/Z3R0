from typing import List, Optional, Union

import discord
from discord.ext import menus


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
    def __init__(self, source, ping=False):
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


class ZMenuPagesView(discord.ui.View):
    """Menus made out of Discord "View" components

    Accept list of str, dict, or discord.Embed

    Also accepts menus.PageSource for compatibility
    """

    def __init__(
        self,
        ctx,
        source: Union[menus.PageSource, Pages],
        timeout: float = 180.0,
        autoDefer: bool = True,
    ) -> None:
        super().__init__(timeout=timeout)
        self.context = ctx
        self._source: Union[menus.PageSource, Pages] = source
        self._message: Optional[discord.Message] = None
        self.currentPage: int = 0
        self.autoDefer: bool = autoDefer

    def getMaxPages(self):
        source = self._source
        return len(source) if isinstance(source, list) else source.get_max_pages()

    async def getKwargsFromPage(self, page):
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

    async def getPage(self, pageNumber):
        source = self._source
        if isinstance(source, list):
            page = pageNumber
        else:
            page = await source.get_page(pageNumber)

        return await self.getKwargsFromPage(page)

    async def sendInitialMessage(self, ctx):
        kwargs = await self.getPage(0)
        self._pageInfo.label = f"Page 1/{self.getMaxPages()}"
        return await ctx.send(view=self, **kwargs)

    async def sendPage(self, interaction: discord.Interaction, pageNumber):
        if self.autoDefer:
            await interaction.response.defer()

        kwargs = await self.getPage(pageNumber)
        self.currentPage = pageNumber
        self._pageInfo.label = f"Page {pageNumber+1}/{self.getMaxPages()}"
        await interaction.message.edit(view=self, **kwargs)

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

    async def start(self):
        self._message = await self.sendInitialMessage(self.context)

    async def finalize(self, timedOut: bool):
        if self._message:
            await self._message.edit(view=None)
        super().stop()

    async def stop(self):
        await self.finalize(False)

    async def on_timeout(self):
        await self.finalize(True)

    @discord.ui.button(emoji="⏪")
    async def _first(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.sendPage(interaction, 0)

    @discord.ui.button(emoji="◀️")
    async def _back(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.sendCheckedPage(interaction, self.currentPage - 1)

    @discord.ui.button(label="Page NaN/NaN", disabled=True)
    async def _pageInfo(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        pass

    @discord.ui.button(emoji="▶️")
    async def _forward(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.sendCheckedPage(interaction, self.currentPage + 1)

    @discord.ui.button(emoji="⏩")
    async def _last(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.sendPage(interaction, self.getMaxPages() - 1)

    @discord.ui.button(
        label="Stop paginator", emoji="\u23F9", style=discord.ButtonStyle.red
    )
    async def _stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.stop()
