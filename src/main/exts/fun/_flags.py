from discord.ext import commands


class FindseedFlags(commands.FlagConverter, case_insensitive=True):
    mode: str = "visual"

    @classmethod
    async def convert(cls, context, mode: str):
        if not mode.startswith("mode:"):
            mode = f"mode: {mode}"
        return await super().convert(context, mode)
