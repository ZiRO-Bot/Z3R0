import aiosqlite
import discord

from discord.ext import commands

class CommandManager(commands.Cog):
    def __init__(self, bot):
        """Manage commands (both built-in and user-made), also handle user-made commands"""
        self.bot = bot

    
def setup(bot):
    bot.add_cog(CommandManager(bot))
