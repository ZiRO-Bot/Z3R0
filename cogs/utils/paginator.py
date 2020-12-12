import asyncio
import discord

from discord.ext import menus


class FunctionPageSource(menus.PageSource):
    """
    PageSource for function, useful for `>anime search|info` since it's not returning list
    """
    def __init__(self, ctx, per_page: int=1):
        self.per_page = per_page
        self.cache = {}
        self.ctx = ctx

    async def prepare(self):
        """Get first page from function and probably cache it and get pagination info such as last page."""
        self.last_page = None
        raise NotImplementedError
    
    def is_paginating(self):
        if not self.last_page:
            raise NotImplementedError
        return self.last_page > self.per_page

    def get_max_pages(self):
        if not self.last_page:
            raise NotImplementedError
        return self.last_page
    
    async def get_page(self, page_number):
        """Get the rest of the page from the function."""
        raise NotImplementedError


class ZiMenu(menus.MenuPages):
    def __init__(self, source, init_msg=None, check_embeds=True, ping=False, loop=None):
        super().__init__(source=source, check_embeds=check_embeds)
        self.ping = ping
        self.init_msg = init_msg

    async def start(self, ctx):
        if not self.init_msg:
            e = discord.Embed(title=f"<a:loading:776255339716673566> Loading...", colour=discord.Colour.rounded())
            self.init_msg = await ctx.channel.send(embed=e)
        await super().start(ctx)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if self.init_msg:
            await self.init_msg.edit(**kwargs)
            return self.init_msg
    
    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.bot.http.remove_reaction(
                    payload.channel_id, payload.message_id,
                    discord.Message._emoji_reaction(payload.emoji), payload.member.id
                )
            elif payload.event_type == 'REACTION_REMOVE':
                return
        await super().update(payload)

    async def finalize(self, timed_out):
        try:
            await self.message.clear_reactions()
        except discord.HTTPException:
            pass

class ZiReplyMenu(ZiMenu):
    def __init__(self, source, ping=False):
        self.ping = ping
        super().__init__(source=source, check_embeds=True)
    
    async def start(self, ctx):
        if not self.init_msg:
            e = discord.Embed(title=f"<a:loading:776255339716673566> Loading...", colour=discord.Colour.rounded())
            self.init_msg = await ctx.reply(embed=e)
        await super().start(ctx)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        await self.init_msg.edit(**kwargs)
        return self.init_msg

    async def _get_kwargs_from_page(self, page):
        no_ping = {'mention_author': False if not self.ping else True}
        value = await discord.utils.maybe_coroutine(self._source.format_page, self, page)
        if isinstance(value, dict):
            return value.update(no_ping)
        elif isinstance(value, str):
            no_ping.update({'content': value})
        elif isinstance(value, discord.Embed):
            no_ping.update({'embed': value})
        return no_ping
