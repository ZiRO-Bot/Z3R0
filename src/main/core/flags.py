"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ..utils.format import separateStringFlags


if TYPE_CHECKING:
    from typing_extensions import Self  # type: ignore - A bug from pyright


# New features from discord.py v2.0, will be replacing ArgumentParser
class StringAndFlags(commands.FlagConverter):
    """FlagConverter with similar behaviour as ArgumentParser

    `string flag: value` -> ('string', parsedFlags)
    """

    def __init__(self):
        super().__init__()
        self.string: str | None = None

    @classmethod
    async def convert(cls, ctx, arguments: str) -> Self:
        string, arguments = separateStringFlags(arguments)
        self: Self = await super().convert(ctx, arguments)
        self.string = string
        return self


# TODO: Ditch flags for greetings, it breaks TagScript handler
class GreetingFlags(commands.FlagConverter, case_insensitive=True):
    channel: discord.TextChannel | None = commands.flag(name="channel", aliases=["ch"], default=None)
    raw: bool = False
    disable: bool = False
    messages: list[str] = commands.flag(name="message", aliases=["msg"], default=[])
