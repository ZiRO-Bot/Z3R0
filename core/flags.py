from typing import List, Optional

import discord
from discord.ext import commands

from utils.format import separateStringFlags


# New features from discord.py v2.0, will be replacing ArgumentParser
class StringAndFlags(commands.FlagConverter):
    @classmethod
    async def convert(cls, ctx, arguments: str):
        string, arguments = separateStringFlags(arguments)
        parsed = await super().convert(ctx, arguments)
        return string, parsed


class GreetingFlags(commands.FlagConverter, case_insensitive=True):
    channel: Optional[discord.TextChannel] = commands.flag(aliases=("ch",))
    raw: bool = commands.flag(aliases=("r",), default=False)
    disable: bool = commands.flag(aliases=("d",), default=False)
    messages: List[str] = commands.flag(name="message", aliases=("msg",), default=[])


class LogConfigFlags(commands.FlagConverter, case_insensitive=True):
    disable: bool = commands.flag(aliases=("d",), default=False)
    channel: Optional[discord.TextChannel] = commands.flag(aliases=("ch",))


class RoleCreateFlags(commands.FlagConverter, case_insensitive=True):
    type_: Optional[str] = commands.flag(name="type")
    nameList: List[str] = commands.flag(name="name", default=[])


class RoleSetFlags(commands.FlagConverter, case_insensitive=True):
    type_: str = commands.flag(name="type")
    role: Optional[discord.Role]
