from discord.ext import commands
from exts.utils.format import ZEmbed


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def session(self):
        return self.bot.session

    @property
    def db(self):
        return self.bot.db

    async def try_reply(self, content="", *, mention_author=False, **kwargs):
        """Try reply, if failed do send instead"""
        try:
            return await self.reply(content, mention_author=mention_author, **kwargs)
        except:
            if mention_author and content:
                content = f"{self.author.mention}\n{content}"
            return await self.send(content, **kwargs)

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop("file", None)
            return await self.send(
                file=discord.File(fp, filename="message_too_long.txt"), **kwargs
            )
        else:
            return await self.send(content)

    async def error(self, error_message: str):
        e = ZEmbed.error(description=error_message)
        return await self.try_reply(embed=e)
