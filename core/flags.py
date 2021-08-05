from typing import List, Optional

import discord
from discord.ext import commands


# New features from discord.py v2.0, will be replacing ArgumentParser
class GreetingFlags(commands.FlagConverter, case_insensitive=True):
    channel: Optional[discord.TextChannel] = commands.flag(aliases=("ch",))
    raw: bool = commands.flag(aliases=("r",), default=False)
    disable: bool = commands.flag(aliases=("d",), default=False)
    messages: List[str] = commands.flag(name="message", aliases=("msg",), default="")


class HelpFlags(commands.FlagConverter, case_insensitive=True):
    filters: List[str] = commands.flag(name="filter", aliases=("filters", "filt"))
