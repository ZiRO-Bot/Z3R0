from discord.ext import commands


class AnimeSearchFlags(commands.FlagConverter, case_insensitive=True):
    format_: str = commands.flag(name="format", default="TV")
