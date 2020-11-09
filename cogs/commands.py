import asyncio
import datetime
import discord
import git
import json
import logging
import os
import random
import time

from .utils.tse_blocks import RandomBlock
from .utils.embed_formatting import em_ctx_send_error
from .utils.formatting import realtime
from .utils.stringparamadapter import StringParamAdapter
from bot import get_cogs
from discord.errors import Forbidden
from discord.ext import commands, menus
from pytz import timezone
from TagScriptEngine import Verb, Interpreter, adapter, block


class CommandsPageSource(menus.ListPageSource):
    def __init__(self, ctx, commands):
        super().__init__(entries=list(commands.keys()), per_page=12)
        self.commands = commands
        self.ctx = ctx

    def format_page(self, menu, commands):
        _list = ""
        for cmd in commands:
            places = {1: "🥇", 2: "🥈", 3: "🥉"}
            pos = self.commands[cmd]["pos"]
            if pos in places:
                pos = places[pos]
            else:
                pos = f"{pos}."
            _list += f"{pos} {cmd} **[{int(self.commands[cmd]['uses'])} uses]**\n"
        e = discord.Embed(
            title="Custom Commands", color=discord.Colour(0xFFFFF0), description=_list
        )
        maximum = self.get_max_pages()
        e.set_footer(
            text=f"Requested by {self.ctx.author} - Page {menu.current_page + 1}/{maximum}",
            icon_url=self.ctx.author.avatar_url,
        )
        return e


class HelpPages(menus.MenuPages):
    def __init__(self, source):
        super().__init__(source=source, check_embeds=True)

    async def finalize(self, timed_out):
        try:
            await self.message.clear_reactions()
        except discord.HTTPException:
            pass


class Custom(commands.Cog):
    """All about custom commands."""

    def __init__(self, bot):
        self.logger = logging.getLogger("discord")
        self.bot = bot
        self.db = self.bot.pool
        bot.loop.create_task(self.create_table())
        self.blocks = [
            RandomBlock(),
            block.StrictVariableGetterBlock(),
            block.MathBlock(),
            block.RangeBlock(),
        ]
        self.engine = Interpreter(self.blocks)

    async def create_table(self):
        """
        Try to create empty table on init.
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """CREATE TABLE IF NOT EXISTS tags
                    (id SERIAL, guild_id text, name text, content text, created int, modified int, uses real, author text)"""
                )

    def clean_tag_content(self, content):
        return content.replace("@everyone", "@\u200beveryone").replace(
            "@here", "@\u200bhere"
        )

    def proper_user(self, user: discord.User):
        """Print user properly (ex: user#6969)."""
        return f"{user.name}#{user.discriminator}"

    def fetch_tags(self, ctx, message):
        # TSE's documentation is pretty bad so this is my workaround for now
        special_vals = {
            "mention": adapter.StringAdapter(ctx.author.mention),
            "user": StringParamAdapter(
                ctx.author.name,
                {
                    "id": str(ctx.author.id),
                    "proper": f"{ctx.author.name}#{ctx.author.discriminator}",
                    "mention": ctx.author.mention,
                },
            ),
            "server": StringParamAdapter(
                ctx.guild.name,
                {
                    "id": str(ctx.guild.id),
                    "members": str(len(ctx.guild.members)),
                    "bots": str(len([x for x in ctx.guild.members if x.bot])),
                    "humans": str(len([x for x in ctx.guild.members if not x.bot])),
                    "random": str(self.proper_user(random.choice(ctx.guild.members))),
                    "owner": str(self.proper_user(ctx.guild.owner)),
                    "roles": str(len(ctx.guild.roles)),
                    "channels": str(len(ctx.guild.channels)),
                },
            ),
            "unix": adapter.IntAdapter(int(datetime.datetime.utcnow().timestamp())),
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
            return await em_ctx_send_error(
                ctx,
                f"No command called `{name}` or you don't have a permission to use it",
            )
        self.bot.c.execute(
            "UPDATE tags SET uses = uses + 1 WHERE (name=? AND id=?)",
            (lookup, str(ctx.guild.id)),
        )
        self.bot.conn.commit()
        content = self.fetch_tags(ctx, a[2])
        await ctx.send(content)

    def is_mod():
        def predicate(ctx):
            return ctx.author.guild_permissions.manage_channels

        return commands.check(predicate)

    @commands.command(name="commands", aliases=["tags", "cmds"])
    async def _commands(self, ctx):
        """Alias for command list."""
        await ctx.invoke(self.bot.get_command("command list"))

    @commands.group(
        name="command",
        aliases=["tag", "cmd"],
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
            "SELECT * FROM tags WHERE id=? ORDER BY uses DESC", (str(ctx.guild.id),)
        )
        tags = tags.fetchall()
        if not tags:
            await ctx.send("This server doesn't have custom command")
            return
        tags = {x[1]: {"uses": x[5], "pos": tags.index(x) + 1} for x in tags}
        menu = HelpPages(CommandsPageSource(ctx, tags))
        await menu.start(ctx)

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
    bot.add_cog(Custom(bot))
