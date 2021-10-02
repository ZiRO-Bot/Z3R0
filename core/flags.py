from typing import Any, List, Optional, Tuple

import discord
from discord.ext import commands

from utils.format import separateStringFlags


# New features from discord.py v2.0, will be replacing ArgumentParser
class StringAndFlags(commands.FlagConverter):
    """FlagConverter with similar behaviour as ArgumentParser

    `string flag: value` -> ('string', parsedFlags)
    """

    @classmethod
    async def _construct_default(cls, ctx) -> Tuple[None, Any]:
        return None, await super()._construct_default(ctx)

    @classmethod
    async def convert(cls, ctx, arguments: str) -> Tuple[str, Any]:
        string, arguments = separateStringFlags(arguments)
        return string, await super().convert(ctx, arguments)


class GreetingFlags(commands.FlagConverter, case_insensitive=True):
    channel: Optional[discord.TextChannel]
    raw: bool = False
    disable: bool = False
    messages: List[str] = commands.flag(name="message", aliases=("msg",), default=[])  # type: ignore


class LogConfigFlags(commands.FlagConverter, case_insensitive=True):
    disable: bool = False
    channel: Optional[discord.TextChannel]


class RoleCreateFlags(commands.FlagConverter, case_insensitive=True):
    type_: Optional[str] = commands.flag(name="type")
    nameList: List[str] = commands.flag(name="name", default=[])


class RoleSetFlags(commands.FlagConverter, case_insensitive=True):
    type_: str = commands.flag(name="type")
    role: Optional[discord.Role]
