"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from discord.ext import commands

from ...core.flags import StringAndFlags
from ...utils.format import separateStringFlags


class AnimeSearchFlags(StringAndFlags, case_insensitive=True):
    name: str = commands.flag(name="name")
    format_: str = commands.flag(name="format", default=None)

    @classmethod
    async def convert(cls, ctx, arguments: str):
        try:
            self = await super().convert(ctx, arguments)
        except commands.MissingFlagArgument:
            string, args = separateStringFlags(arguments)
            args += f" name:{string}"
            return await super().convert(ctx, args)

        if not self.string:
            return self

        self.name = self.string
        return self
