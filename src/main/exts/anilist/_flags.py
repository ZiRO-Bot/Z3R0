from discord.ext import commands

from ...core.flags import StringAndFlags


class AnimeSearchFlags(StringAndFlags, case_insensitive=True):
    format_: str = commands.flag(name="format", default=None)
