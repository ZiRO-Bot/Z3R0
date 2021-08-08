from typing import List

from discord.ext import commands

from core.flags import StringAndFlags


class HelpFlags(StringAndFlags, case_insensitive=True):
    filters: List[str] = commands.flag(
        name="filter", aliases=("filters", "filt"), default=[]
    )
