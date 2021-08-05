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


class ZMenuView:
    pass
