import io
from contextlib import asynccontextmanager
from typing import Union

import aiohttp
import discord
from discord.ext import commands

from .embed import ZEmbed


class Context(commands.Context):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    # @property
    # def db(self):
    #     return self.bot.db

    @property
    def cache(self):
        return self.bot.cache

    async def try_reply(self, content=None, *, mention_author=False, **kwargs):
        """Try reply, if failed do send instead"""
        if self.interaction is None or self.interaction.is_expired():
            try:
                action = self.safe_reply
                return await action(content, mention_author=mention_author, **kwargs)
            except BaseException:
                if mention_author:
                    content = f"{self.author.mention} " + content if content else ""

                action = self.safe_send
                return await self.safe_send(content, **kwargs)

        return await self.send(content, **kwargs)

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

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        return await self.safe_send_reply(content, escape_mentions=escape_mentions, type="send", **kwargs)

    async def safe_reply(self, content, *, escape_mentions=True, **kwargs):
        return await self.safe_send_reply(content, escape_mentions=escape_mentions, type="reply", **kwargs)

    async def error(self, error_message: str = None, title: str = "Something went wrong!"):
        e = ZEmbed.error(title="ERROR" + (f": {title}" if title else ""))
        if error_message is not None:
            e.description = str(error_message)
        return await self.try_reply(embed=e)

    async def success(self, success_message: str = None, title: str = None):
        e = ZEmbed.success(
            title=title or "Success",
        )
        if success_message is not None:
            e.description = str(success_message)
        return await self.try_reply(embed=e)

    @asynccontextmanager
    async def loading(self, title: str = None):
        """
        async with ctx.loading(title="This param is optional"):
            await asyncio.sleep(5) # or any long process stuff
            await ctx.send("Finished")
        """
        if self.interaction:
            yield await self.interaction.response.defer()
            return

        e = ZEmbed.loading(title=title or "Loading...")
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
            command: commands.Command = self.bot.get_command(command)

        canRun = await command.can_run(self)
        if canRun:
            await command(self, *args, **kwargs)

    @discord.utils.cached_property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None
