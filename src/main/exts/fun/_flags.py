from typing import Literal

from discord.ext import commands
from discord.ext.commands.errors import BadLiteralArgument


FINDSEED_MODES = Literal["visual", "classic", "pipega", "halloween"]


class FindseedFlags(commands.FlagConverter, case_insensitive=True):
    mode: FINDSEED_MODES = "visual"

    @classmethod
    async def convert(cls, context, mode: str):
        if not mode.startswith("mode:"):
            mode = f"mode: {mode}"
        try:
            return await super().convert(context, mode)
        except BadLiteralArgument:
            return "visual"
