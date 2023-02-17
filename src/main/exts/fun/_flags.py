"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from typing import Literal

from discord.ext import commands
from discord.ext.commands.errors import BadLiteralArgument


FINDSEED_MODES = Literal["visual", "classic", "pipega", "halloween"]


class FindseedFlags(commands.FlagConverter, case_insensitive=True):
    mode: FINDSEED_MODES = "visual"

    @classmethod
    async def convert(cls, context, mode: str):
        if not mode.startswith("mode:") and context.interaction:
            mode = f"mode: {mode}"
        try:
            return await super().convert(context, mode)
        except BadLiteralArgument:
            return "visual"
