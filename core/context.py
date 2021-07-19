import discord
import re


from discord.ext import commands
from exts.utils.format import ZEmbed
from typing import Union, Optional


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def session(self):
        return self.bot.session

    @property
    def db(self):
        return self.bot.db

    async def try_reply(self, content=None, *, mention_author=False, **kwargs):
        """Try reply, if failed do send instead"""
        try:
            action = self.safe_reply
            return await action(content, mention_author=mention_author, **kwargs)
        except:
            if mention_author:
                content = f"{self.author.mention} " + content if content else ""

            action = self.safe_send
            return await self.safe_send(content, **kwargs)

    async def safe_send_reply(
        self, content, *, escape_mentions=True, type="send", **kwargs
    ):
        action = getattr(self, type)

        if escape_mentions and content is not None:
            content = discord.utils.escape_mentions(content)

        if content is not None and len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop("file", None)
            return await action(
                file=discord.File(fp, filename="message_too_long.txt"), **kwargs
            )
        else:
            if content is not None:
                kwargs["content"] = content
            return await action(**kwargs)

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        return await self.safe_send_reply(
            content, escape_mentions=escape_mentions, type="send", **kwargs
        )

    async def safe_reply(self, content, *, escape_mentions=True, **kwargs):
        return await self.safe_send_reply(
            content, escape_mentions=escape_mentions, type="reply", **kwargs
        )

    async def error(
        self, error_message: str = None, title: str = "Something went wrong!"
    ):
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

    @property
    def clean_prefix(self):
        pattern = re.compile(r"<@!?{}>".format(self.me.id))
        return pattern.sub(
            "@{}".format(self.me.display_name.replace("\\", r"\\")), self.prefix
        )

    async def try_invoke(self, command: Union[commands.Command, str], *args, **kwargs):
        """Similar to invoke() except it triggers checks"""
        if isinstance(command, str):
            command = self.bot.get_command(command)

        canRun = await command.can_run(self)
        if canRun:
            await command(self, *args, **kwargs)
