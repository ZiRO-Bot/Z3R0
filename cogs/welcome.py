import asyncio
import discord
import logging

from discord.ext import commands
from random import randint

class Welcome(commands.Cog, name="Welcome"):
    # Welcome message + set roles when new member joined
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcome_msg=[f"It's a Bird, It's a Plane, It's {member.mention}!",
                f"Welcome {member.mention}! <:PogChamp:740102448047194152>",
                f"Good to see you, {member.mention}.",
                f"A wild {member.mention} appeared!"]
        
        server = member.guild
        welcome_channel = self.bot.get_channel(
                                               int(self.bot.channels[
                                                   str(server.id)][
                                                       "welcome_ch"]
                                                  )
                                              )
        member_role = discord.utils.get(member.guild.roles, name="Member")
        await member.add_roles(member_role)
        await welcome_channel.send(f"{welcome_msg[randint(0, len(welcome_msg) - 1)]}")

def setup(bot):
    bot.add_cog(Welcome(bot))
