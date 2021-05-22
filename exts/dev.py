import discord


from exts.utils import infoQuote
from discord.ext import commands


class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return self.bot.master and ctx.author.id in self.bot.master

    @commands.group(invoke_without_command=True)
    async def test(self, ctx):
        """Test something."""
        await ctx.send(infoQuote.info("Test") + " hello")

    @test.command()
    async def error(self, ctx):
        """Test error handler."""
        raise RuntimeError("Haha error brrr")


def setup(bot):
    bot.add_cog(Developer(bot))
