from discord.ext import commands

def formatName(name: str):
    return name.lower().replace(" ", "-")

class CMDName(commands.Converter):
    async def convert(self, ctx, argument: str):
        return formatName(argument)
