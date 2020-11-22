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
                    """
                    CREATE TABLE IF NOT EXISTS 
                    tags (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE NOT NULL,
                        name TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created TIMESTAMP WITH TIME ZONE,
                        modified TIMESTAMP WITH TIME ZONE,
                        uses INT DEFAULT 0,
                        author BIGINT
                    )
                    """
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
                    "proper": str(ctx.author),
                    "mention": ctx.author.mention,
                    "nick": ctx.author.nick or ctx.author.name,
                },
            ),
            "server": StringParamAdapter(
                ctx.guild.name,
                {
                    "id": str(ctx.guild.id),
                    "members": str(len(ctx.guild.members)),
                    "bots": str(len([x for x in ctx.guild.members if x.bot])),
                    "humans": str(len([x for x in ctx.guild.members if not x.bot])),
                    "random": str(random.choice(ctx.guild.members)),
                    "owner": str(ctx.guild.owner),
                    "roles": str(len(ctx.guild.roles)),
                    "channels": str(len(ctx.guild.channels)),
                },
            ),
            "unix": adapter.IntAdapter(int(datetime.datetime.utcnow().timestamp())),
        }
        return self.engine.process(message, special_vals).body

    async def send_tag_content(self, ctx, name):
        lookup = name.lower().strip()
        a = await ctx.db.fetchrow(
            """
            SELECT name, content
            FROM tags
            WHERE guild_id=$1 AND LOWER(name)=$2
            """,
            ctx.guild.id,
            lookup,
        )

        # -- Legacy stuff, delete later
        # self.bot.c.execute(
        #     "SELECT * FROM tags WHERE (name = ? AND id = ?)",
        #     (lookup, str(ctx.guild.id)),
        # )
        # a = self.bot.c.fetchone()
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
        content = self.fetch_tags(ctx, a["content"])
        await ctx.safe_send(content)
        await ctx.db.execute(
            "UPDATE tags SET uses = uses + 1 WHERE guild_id=$1 AND name=$2",
            ctx.guild.id,
            a["name"],
        )

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

        await ctx.acquire()

        a = await ctx.db.fetch(
            "SELECT * FROM tags WHERE (name = $1 AND guild_id = $2)",
            lookup,
            ctx.guild.id,
        )
        if a:
            await em_ctx_send_error(ctx, "Command already exists!")
            await ctx.release()
            return
        # content = self.clean_tag_content(content)
        async with ctx.db.transaction():
            await ctx.db.execute(
                """INSERT INTO tags 
                (guild_id, name, content, created, modified, author) 
                VALUES ($1, $2, $3, $4, $5, $6)""",
                ctx.guild.id,
                lookup,
                content,
                datetime.datetime.now(),
                datetime.datetime.now(),
                ctx.message.author.id,
            )
        await ctx.release()
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
        # content = self.clean_tag_content(content)
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
        a = await ctx.db.fetch(
            "SELECT * FROM tags WHERE guild_id = $1 AND name = $2",
            ctx.guild.id, lookup
        )
        if not a:
            return await em_ctx_send_error(ctx, f"There's no command called `{name}`")
        await ctx.db.execute(
            "DELETE FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, lookup
        )
        await ctx.send(f"Command `{name}` has been deleted")

    @custom.command(name="list", aliases=["ls"])
    async def command_list(self, ctx):
        """Show all custom commands."""
        tags = await ctx.db.fetch(
            "SELECT * FROM tags WHERE guild_id=$1 ORDER BY uses DESC", ctx.guild.id,
        )
        if not tags:
            await ctx.send("This server doesn't have custom command")
            return
        tags = {x['name']: {"uses": x['uses'], "pos": tags.index(x) + 1} for x in tags}
        menu = HelpPages(CommandsPageSource(ctx, tags))
        await menu.start(ctx)

    @custom.command(name="info", aliases=["?"], usage="(command name)")
    async def command_info(self, ctx, name: str):
        """Show information of a custom command."""
        jakarta = timezone("Asia/Jakarta")
        lookup = name.lower()
        
        a = await ctx.db.fetchrow(
            """
            SELECT name, created, modified, uses, author
            FROM tags
            WHERE guild_id = $1 AND name = $2
            """,
            ctx.guild.id,
            lookup
        )
        if not a:
            return
        
        rc = await ctx.db.fetch(
            """
            SELECT uses
            FROM tags
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        rank = sorted([x[0] for x in rc], reverse=True).index(a['uses']) + 1

        e = discord.Embed(
            title=f"Custom Command - {a['name']}", color=discord.Colour(0xFFFFF0)
        )

        e.add_field(name="Owner", value=f"<@{a['author']}>")
        e.add_field(name="Uses", value=int(a['uses']))
        e.add_field(name="Rank", value=rank)
        e.add_field(
            name="Created at",
            value=a['created'].replace(tzinfo=timezone("UTC"))
            .astimezone(jakarta)
            .strftime("%a, %#d %B %Y, %H:%M WIB"),
        )
        e.add_field(
            name="Last modified",
            value=a['modified'].replace(tzinfo=timezone("UTC"))
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
