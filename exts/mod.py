import discord


from discord.ext import commands


class Mod(commands.Cog):
    """Moderation commands."""
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Mod(bot))
