import asyncio
import datetime
import discord
import git
import json
import logging
import os
import time

from .utilities.embed_formatting import em_ctx_send_error
from .utilities.formatting import realtime
from .utilities.stringparamadapter import StringParamAdapter
from bot import get_cogs
from discord.errors import Forbidden
from discord.ext import commands
from pytz import timezone
from TagScriptEngine import Verb, Interpreter, adapter, block
from blocks import zibot


class CustomCommands(commands.Cog, name="customcommands"):
    def __init__(self, bot):
        self.logger = logging.getLogger("discord")
        self.bot = bot
        self.bot.c.execute(
            """CREATE TABLE IF NOT EXISTS tags
                (id text, name text, content text, created int, updated int, uses real, author text)"""
        )
        self.blocks = [block.RandomBlock(), block.StrictVariableGetterBlock()]
        self.engine = Interpreter(self.blocks)

    def clean_tag_content(self, content):
        return content.replace("@everyone", "@\u200beveryone").replace(
            "@here", "@\u200bhere"
        )

    def fetch_blocks(self, ctx, message):
        # TSE's documentation is pretty bad so this is my workaround for now
        special_vals = {
            "mention": adapter.StringAdapter(ctx.author.mention),
            "user": StringParamAdapter(
                ctx.author.name,
                {
                    "id": str(ctx.author.id),
                    "proper": f"{ctx.author.name}#{ctx.author.discriminator}",
                },
            ),
            "server": adapter.StringAdapter(ctx.guild.name),
        }
        return self.clean_tag_content(self.engine.process(message, special_vals).body)

    async def send_tag_content(self, ctx, name):
        lookup = name.lower().strip()
        self.bot.c.execute(
            "SELECT * FROM tags WHERE (name = ? AND id = ?)",
            (lookup, str(ctx.guild.id)),
        )
        a = self.bot.c.fetchone()
        self.bot.c.execute(
            "SELECT send_error_msg FROM settings WHERE (id = ?)",
            (str(ctx.guild.id),),
        )
        send_err = self.bot.c.fetchone()
        if not a:
            if send_err[0] == 0 or (
                ctx.prefix == "@" and (lookup == "everyone" or lookup == "here")
            ):
                return
            return await em_ctx_send_error(ctx, f"No command called `{name}`")
        self.bot.c.execute(
            "UPDATE tags SET uses = uses + 1 WHERE (name=? AND id=?)",
            (lookup, str(ctx.guild.id)),
        )
        self.bot.conn.commit()
        content = self.fetch_blocks(ctx, a[2])
        await ctx.send(content)

    def is_mod():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels

        return commands.check(predicate)

    @commands.group(
        name="command",
        aliases=["tag", "customcommand"],
        invoke_without_command=True,
        usage="(command name)",
    )
    async def custom(self, ctx, name: str):
        """Manage custom commands."""
        await self.send_tag_content(ctx, name)

    @custom.command(name="get", hidden=True)
    async def command_get(self, ctx, name: str):
        await self.send_tag_content(ctx, name)

    @custom.command(
        name="add", aliases=["+", "create"], usage="(command name) (content)"
    )
    async def command_add(self, ctx, name: str, *, content: str):
        """Add new custom command."""
        if ctx.message.mentions:
            return
        lookup = name.lower().strip()
        try:
            self.verify_lookup(lookup)
        except RuntimeError as e:
            return await em_ctx_send_error(ctx, e)

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

    @custom.command(name="edit", aliases=["&", "ed"], usage="(command name) (content)")
    async def command_edit(self, ctx, name: str, *, content: str):
        """Edit a custom command."""
        if ctx.message.mentions:
            return
        lookup = name.lower().strip()
        try:
            self.verify_lookup(lookup)
        except RuntimeError as e:
            return await em_ctx_send_error(ctx, e)

        self.bot.c.execute(
            "SELECT * FROM tags WHERE (name = ? AND id = ?)",
            (lookup, str(ctx.guild.id)),
        )
        a = self.bot.c.fetchall()
        if not a:
            return await em_ctx_send_error(ctx, f"There's no command called `{name}`")
        content = self.clean_tag_content(content)
        self.bot.c.execute(
            "UPDATE tags SET content = ?, updated = ? WHERE (name = ? AND id = ?)",
            (
                content,
                datetime.datetime.utcnow().timestamp(),
                lookup,
                str(ctx.guild.id),
            ),
        )
        self.bot.conn.commit()
        await ctx.send(f"Command `{name}` has been edited")

    @custom.command(
        name="remove", aliases=["-", "rm", "delete", "del"], usage="(command name)"
    )
    async def command_rm(self, ctx, name: str):
        """Remove a custom command."""
        lookup = name.lower()
        self.bot.c.execute(
            "SELECT * FROM tags WHERE (name = ? AND id = ?)",
            (lookup, str(ctx.guild.id)),
        )
        a = self.bot.c.fetchone()
        if not a:
            return await em_ctx_send_error(ctx, f"There's no command called `{name}`")
        self.bot.c.execute(
            "DELETE FROM tags WHERE (name = ? AND id = ?)", (lookup, str(ctx.guild.id))
        )
        self.bot.conn.commit()
        await ctx.send(f"Command `{name}` has been deleted")

    @custom.command(name="list", aliases=["ls"])
    async def command_list(self, ctx):
        """Show all custom commands."""
        tags = self.bot.c.execute(
            "SELECT name FROM tags WHERE id=? ORDER BY uses DESC", (str(ctx.guild.id),)
        )
        tags = tags.fetchall()
        tags = [x[0] for x in tags]
        if tags:
            e = discord.Embed(title="Custom Commands")
            e.description = ""
            for tag in tags:
                e.description += f"{tags.index(tag) + 1}. {tag}\n"
            await ctx.send(embed=e)
        else:
            await ctx.send("This server doesn't have custom command")

    @custom.command(name="info", aliases=["?"], usage="(command name)")
    async def command_info(self, ctx, name: str):
        """Show information of a custom command."""
        jakarta = timezone("Asia/Jakarta")
        lookup = name.lower()
        self.bot.c.execute(
            "SELECT * FROM tags WHERE (name = ? AND id = ?)",
            (lookup, str(ctx.guild.id)),
        )
        _, name, _, created, updated, uses, author = self.bot.c.fetchone()
        if not name:
            return
        self.bot.c.execute("SELECT uses FROM tags WHERE id=?", (str(ctx.guild.id),))
        rc = self.bot.c.fetchall()
        rank = sorted([x[0] for x in rc], reverse=True).index(uses) + 1
        e = discord.Embed(
            title=f"Custom Command - {name}", color=discord.Colour(0xFFFFF0)
        )
        e.add_field(name="Owner", value=f"<@{author}>")
        e.add_field(name="Uses", value=int(uses))
        e.add_field(name="Rank", value=rank)
        e.add_field(
            name="Created at",
            value=datetime.datetime.fromtimestamp(created)
            .replace(tzinfo=timezone("UTC"))
            .astimezone(jakarta)
            .strftime("%a, %#d %B %Y, %H:%M WIB"),
        )
        e.add_field(
            name="Last updated",
            value=datetime.datetime.fromtimestamp(updated)
            .replace(tzinfo=timezone("UTC"))
            .astimezone(jakarta)
            .strftime("%a, %#d %B %Y, %H:%M WIB"),
        )
        e.set_footer(
            text=f"Requested by {ctx.message.author.name}#{ctx.message.author.discriminator}"
        )
        await ctx.send(embed=e)

    def verify_lookup(self, lookup):
        if "@everyone" in lookup or "@here" in lookup:
            raise RuntimeError("That command is using blocked words.")

        if not lookup:
            raise RuntimeError("You need to actually pass in a command name.")

        if len(lookup) > 50:
            raise RuntimeError("Command name is a maximum of 50 characters.")


def setup(bot):
    bot.add_cog(CustomCommands(bot))
