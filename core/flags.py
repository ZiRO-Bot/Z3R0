from typing import List, Optional

import discord
from discord.ext import commands
from discord.utils import MISSING


# Only available in dpy V2.0
class GreetingFlag(commands.FlagConverter):
    channel: Optional[discord.TextChannel] = MISSING
    disable: Optional[bool] = False
    message: str


class HelpFlag(commands.FlagConverter):
    filters: List[str] = commands.flag(name="filter", aliases=("filters", "filt"))
