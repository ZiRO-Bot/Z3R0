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
                (id text unique, name text, content text, created int, updated int, uses real, author text)"""
        )

    def clean_tag_content(self, content):
        return content.replace("@everyone", "@\u200beveryone").replace(
            "@here", "@\u200bhere"
        )

    async def send_tag_content(self, ctx, name):
        pass

    @commands.group()
    async def tag(self, ctx, name: str):
        pass

    @tag.command(aliases=['+', 'create'])
    async def add(self, ctx, name, *, content: str):
        pass


def setup(bot):
    bot.add_cog(CustomCommands(bot))
