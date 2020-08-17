import discord
import asyncio
import logging

from discord.ext import commands

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
    
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
        embed.add_field(name="Message", value=f"{msg}", inline=False)
        await purgatory_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        message = before
        purgatory_ch = self.bot.get_channel(741431840958578811)
        embed = discord.Embed(title = "Edited Message",
                colour = discord.Colour.red())
        embed.add_field(name="User", value=f"{message.author.mention}")
        embed.add_field(name="Channel", value=f"{message.channel.mention}")
        if not message.content:
            b_msg = "None"
        else:
            b_msg = message.content
        if not after.content:
            a_msg = "None"
        else:
            a_msg = after.content
        embed.add_field(name="Before", value=f"{b_msg}", inline=False)
        embed.add_field(name="After", value=f"{a_msg}", inline=False)
        await purgatory_ch.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Tell the ping of the bot to the discord servers"""
        self.logger.info("Hello world!")
        await ctx.send(f'Pong! {round(self.bot.latency*1000)}ms')

def setup(bot):
    bot.add_cog(Utils(bot))

