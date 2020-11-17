from discord.ext import commands


class Debug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Only bot master able to use debug cogs."""
        return await ctx.bot.is_owner(ctx.author)
    
    @commands.command()
    async def get_prefix(self, ctx):
        prefixes = await self.bot.get_raw_guild_prefixes(ctx.guild.id)
        await ctx.send(prefixes)



def setup(bot):
    bot.add_cog(Debug(bot))
