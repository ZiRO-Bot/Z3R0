import asyncio
import datetime
import discord
import git
import json
import logging
import os
import time

from bot import get_cogs
from discord.errors import Forbidden
from discord.ext import commands
from utilities.formatting import realtime


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("discord")
        self.bot = bot
        self.bot.c.execute(
            """CREATE TABLE IF NOT EXISTS tags
                (id text unique, name text, content text, uses real, author text)"""
        )


def setup(bot):
    bot.add_cog(CustomCommands(bot))
