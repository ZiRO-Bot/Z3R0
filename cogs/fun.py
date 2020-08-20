import asyncio
import datetime
import discord

from discord.ext import commands
from random import randint

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5)
    async def flip(self, ctx):
        coin_side = ['heads', 'tails']
        await ctx.send(f"{ctx.message.author.mention} {coin_side[randint(0, 1)]}")

def setup(bot):
    bot.add_cog(Fun(bot))

