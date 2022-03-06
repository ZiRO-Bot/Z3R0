from discord.ext import commands


class FindseedFlags(commands.FlagConverter, case_insensitive=True):
    mode: str = "visual"
