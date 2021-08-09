from typing import Optional, Union

import discord
from discord.ext import commands

from core.flags import StringAndFlags


class AnnouncementFlags(StringAndFlags, case_insensitive=True):
    target: Union[discord.Role, str] = "everyone"
    channel: Optional[discord.TextChannel] = commands.flag(aliases=("ch",))
