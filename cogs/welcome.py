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
        welcome_msg = [
            f"It's a Bird, It's a Plane, It's {member.mention}!",
            f"Welcome {member.mention}! <:PogChamp:747027389485154354>",
            f"Good to see you, {member.mention}.",
            f"A wild {member.mention} appeared!",
        ]

        server = member.guild

        self.bot.c.execute(
            "SELECT greeting_ch FROM servers WHERE id=?", (str(server.id),)
        )
        welcome_channel = self.bot.c.fetchall()[0][0]
        welcome_channel = server.get_channel(int(welcome_channel))

        self.bot.c.execute(
            "SELECT default_role FROM roles WHERE id=?", (str(server.id),)
        )
        member_role = self.bot.c.fetchall()[0][0]
        member_role = server.get_role(int(member_role))
        if member_role:
            await member.add_roles(member_role)
        if not welcome_channel:
            return
        await welcome_channel.send(f"{welcome_msg[randint(0, len(welcome_msg) - 1)]}")


def setup(bot):
    bot.add_cog(Welcome(bot))
