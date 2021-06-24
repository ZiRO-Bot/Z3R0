import datetime as dt
import discord
import re


from discord.ext import commands


class ZEmbed(discord.Embed):
    def __init__(self, color=0x3DB4FF, fields=(), field_inline=False, **kwargs):
        super().__init__(color=color, **kwargs)
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    @classmethod
    def default(cls, ctx, timestamp=None, **kwargs):
        instance = cls(timestamp=timestamp or dt.datetime.utcnow(), **kwargs)
        instance.set_footer(text="Requested by {}".format(ctx.author), icon_url=ctx.author.avatar_url)
        return instance

    @classmethod
    def error(cls, title="<:error:783265883228340245> Error", color=discord.Color.red(), **kwargs):
        return cls(title=title, color=color, **kwargs)

# def formatDate(datetime = dt.datetime.utcnow()):
#     # Format: 1 Jan 1970 - 00:00 UTC
#     return datetime.strftime("%d %b %Y - %H:%M %Z")

def formatDateTime(datetime):
    return datetime.strftime("%A, %d %b %Y • %H:%M:%S UTC")

def formatName(name: str):
    return name.strip().lower().replace(" ", "-")

class CMDName(commands.Converter):
    async def convert(self, ctx, argument: str):
        return formatName(argument)

def cleanifyPrefix(bot, prefix):
    """Cleanify prefix (similar to context.clean_prefix)"""
    pattern = re.compile(r"<@!?{}>".format(bot.user.id))
    return pattern.sub(
        "@{}".format(bot.user.display_name.replace("\\", r"\\")), prefix
    )

