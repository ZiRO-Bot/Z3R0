import asyncio
import datetime
import discord
import logging

from .utilities.stringparamadapter import StringParamAdapter
from discord.ext import commands
from random import randint
from TagScriptEngine import Verb, Interpreter, adapter, block


class Welcome(commands.Cog, name="welcome"):
    # Welcome message + set roles when new member joined
    def __init__(self, bot):
        self.bot = bot
        # self.engine = Interpreter(self.bot.blocks)
        
    def fetch_special_val(self, member, message):
        engine = self.bot.init_tagscript(self.bot.blocks, member, member.guild)
        special_vals = {
            "unix": adapter.IntAdapter(int(datetime.datetime.utcnow().timestamp())),
        }
        return engine.process(message, special_vals).body

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        server = member.guild

        # Get farewell_msg from database
        self.bot.c.execute(
            f"SELECT farewell_msg FROM settings WHERE id=?", (str(server.id),)
        )
        settings = self.bot.c.fetchone()
        if not settings[0]:
            return
        # fetch special values
        farewell_msg = self.fetch_special_val(member, str(settings[0]))

        # get greet_channel and send the message
        self.bot.c.execute(
            "SELECT greeting_ch FROM servers WHERE id=?", (str(server.id),)
        )
        greet_channel = server.get_channel(int(self.bot.c.fetchone()[0] or 0))
        if greet_channel:
            await greet_channel.send(farewell_msg)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        def_welcome_msg = [
            f"It's a Bird, It's a Plane, It's {member.mention}!",
            f"Welcome {member.mention}! <:PogChamp:747027389485154354>",
            f"Good to see you, {member.mention}.",
            f"A wild {member.mention} appeared!",
        ]

        server = member.guild

        # Get welcome channel
        self.bot.c.execute(
            "SELECT greeting_ch FROM servers WHERE id=?", (str(server.id),)
        )
        welcome_channel = server.get_channel(int(self.bot.c.fetchone()[0] or 0))
        if not welcome_channel:
            return

        self.bot.c.execute(
            f"SELECT welcome_msg FROM settings WHERE id=?", (str(server.id),)
        )
        settings = self.bot.c.fetchone()

        # welcome message
        welcome_msg = (
            self.fetch_special_val(member, str(settings[0]))
            if settings[0]
            else def_welcome_msg[randint(0, len(def_welcome_msg) - 1)]
        )

        # send msg after getting welcome msg
        await welcome_channel.send(welcome_msg)

        self.bot.c.execute(
            "SELECT default_role FROM roles WHERE id=?", (str(server.id),)
        )
        member_role = server.get_role(int(self.bot.c.fetchone()[0] or 0))
        try:
            if member_role:
                await member.add_roles(member_role)
        except TypeError:
            pass


def setup(bot):
    bot.add_cog(Welcome(bot))
