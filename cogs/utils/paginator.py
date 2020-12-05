import discord

from discord.ext import menus


class ZiMenu(menus.MenuPages):
    def __init__(self, source, init_msg=None, check_embeds=True, ping=False):
        super().__init__(source=source, check_embeds=check_embeds)
        self.init_msg = init_msg
        self.ping = ping

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if self.init_msg:
            await self.init_msg.edit(**kwargs)
            return self.init_msg
        return await channel.send(**kwargs)
    
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

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await ctx.reply(**kwargs)

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
