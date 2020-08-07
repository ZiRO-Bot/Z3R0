from discord.ext import commands
import discord
import asyncio

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        purgatory_ch = self.bot.get_channel(741431840958578811)
        embed = discord.Embed(title = "Deleted Message",
                colour = discord.Colour.red())
        embed.add_field(name="User", value=f"{message.author.mention}")
        embed.add_field(name="Channel", value=f"{message.channel.mention}")
        if not message.content:
            msg = "None"
        else:
            msg = message.content
        embed.add_field(name="Message", value=f"{msg}")
        await purgatory_ch.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers"""
        await ctx.send(f'Pong! {round(self.bot.latency*1000)}ms')

def setup(bot):
    bot.add_cog(Utils(bot))

