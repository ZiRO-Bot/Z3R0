from discord.ext import commands

class Debug(commands.Cog, name="debug"):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return await ctx.bot.is_owner(ctx.author)

def setup(bot):
    bot.add_cog(Debug(bot))
