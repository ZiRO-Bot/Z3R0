import discord


from discord.ext import commands
from discord.utils import MISSING
from typing import Optional


# Only available in dpy V2.0
class GreetingFlag(commands.FlagConverter):
    channel: Optional[discord.TextChannel] = MISSING
    disable: Optional[bool] = False
    message: str
