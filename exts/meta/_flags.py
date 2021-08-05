from typing import List

from discord.ext import commands


class HelpFlags(commands.FlagConverter, case_insensitive=True):
    filters: List[str] = commands.flag(
        name="filter", aliases=("filters", "filt"), default=[]
    )
