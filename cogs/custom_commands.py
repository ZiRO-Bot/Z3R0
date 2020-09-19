import asyncio
import datetime
import discord
import git
import json
import logging
import os
import time

from bot import get_cogs
from cogs.utilities.embed_formatting import em_ctx_send_error
from discord.errors import Forbidden
from discord.ext import commands
from utilities.formatting import realtime


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("discord")
        self.bot = bot
        self.bot.c.execute(
            """CREATE TABLE IF NOT EXISTS tags
                (id text, name text, content text, created int, updated int, uses real, author text)"""
        )

    def clean_tag_content(self, content):
        return content.replace("@everyone", "@\u200beveryone").replace(
            "@here", "@\u200bhere"
        )

    async def send_tag_content(self, ctx, name):
        lookup = name.lower().strip()
        self.bot.c.execute(
            "SELECT * FROM tags WHERE (name = ? AND id = ?)",
            (lookup, str(ctx.guild.id)),
        )
        a = self.bot.c.fetchone()
        if not a:
            return await em_ctx_send_error(ctx, f"No command called `{name}`")
        self.bot.c.execute(
            'UPDATE tags SET uses = uses + 1 WHERE (name=? AND id=?)', (lookup, str(ctx.guild.id)))
        self.bot.conn.commit()
        await ctx.send(a[2])

    @commands.group(aliases=['tag', 'customcommand'], invoke_without_command=True)
    async def custom(self, ctx, name: str):
        """Manage custom commands."""
        await self.send_tag_content(ctx, name)

    @custom.command(name="add", aliases=["+", "create"])
    async def command_add(self, ctx, name: str, *, content: str):
        """Add new custom command."""
        lookup = name.lower().strip()
        self.bot.c.execute(
            "SELECT * FROM tags WHERE (name = ? AND id = ?)",
            (lookup, str(ctx.guild.id)),
        )
        a = self.bot.c.fetchone()
        if a:
            await em_ctx_send_error(ctx, "Command already exists!")
            return
        content = self.clean_tag_content(content)
        self.bot.c.execute(
            "INSERT INTO tags VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(ctx.guild.id),
                lookup,
                content,
                datetime.datetime.utcnow().timestamp(),
                datetime.datetime.utcnow().timestamp(),
                0,
                ctx.message.author.id,
            ),
        )
        self.bot.conn.commit()
        await ctx.send(f"Command `{name}` has been created")


def setup(bot):
    bot.add_cog(CustomCommands(bot))
