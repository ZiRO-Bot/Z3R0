from typing import List

from discord.ext import commands

from core.flags import StringAndFlags


class HelpFlags(StringAndFlags, case_insensitive=True):
    filters: List[str] = commands.flag(name="filter", aliases=("filters", "filt"), default=[])


class CmdManagerFlags(StringAndFlags, case_insensitive=True):
    built_in: bool = commands.flag(name="built-in", default=False)
    custom: bool = False
    category: bool = commands.flag(aliases=("cat",), default=False)
