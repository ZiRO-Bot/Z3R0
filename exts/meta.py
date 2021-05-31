"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import discord
import datetime as dt
import humanize


from core.errors import CCommandNotFound
from core.mixin import CogMixin
from exts.utils import dbQuery, infoQuote
from discord.ext import commands


class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        destination = self.get_destination()
        e = discord.Embed(
            description=infoQuote.info(
                "`()`: **Required** | `[]`: **Optional**\n{}".format(
                    ctx.bot.formattedPrefixes(ctx.message),
                )
            ).replace("   ", ""),
            colour=ctx.bot.colour,
        )
        e.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        e.add_field(name="Commands", value="Placeholder")
        await destination.send(embed=e)


# --- NOTE: Edit these stuff to your liking
author = "ZiRO2264#4572"
version = "`v3.0.O` - `overhaul`"
links = {
    "Documentation (Coming Soon)": "",
    "Source Code": "https://github.com/ZiRO-Bot/ziBot",
    "Support Server": "https://discord.gg/sP9xRy6",
}
license = "Mozilla Public License, v. 2.0"
# ---


class Meta(commands.Cog, CogMixin):
    """Bot-related commands."""
    def __init__(self, bot):
        super().__init__(bot)
        # Replace default help menu with custom one
        self._original_help_command = bot.help_command
        self.bot.help_command = CustomHelp()
        self.bot.help_command.cog = self

        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        async with self.db.transaction():
            # commands database table
            await self.db.execute(dbQuery.createCommandsTable)
            # commands_lookup database table
            await self.db.execute(dbQuery.createCommandsLookupTable)

    async def execCustomCommand(self, ctx, command):
        _id = await self.db.fetch_one(
            dbQuery.getCommandId,
            values={"name": command, "guildId": ctx.guild.id}
        )
        if not _id:
            # No command found
            raise CCommandNotFound(command)
        result = await self.db.fetch_one(
            dbQuery.getCommandContent,
            values={"id": _id[0]}
        )
        async with self.db.transaction():
            # Increment uses
            await self.db.execute(
                dbQuery.incrCommandUsage,
                values={"id": _id[0]}
            )
            return await ctx.send(result[0])

    # TODO: Adds custom check with usage limit (
    #     0: Only mods,
    #     1: Partial (Can only add/edit/remove their own command),
    #     2: Full (Can do anything to any existing command in the guild)
    # )
    # Also separate tags from custom command later on
    @commands.group(aliases=["cmd", "tag", "script"], invoke_without_command=True)
    async def command(self, ctx, name: str, argument: str = None):
        """Manage commands"""
        return await self.execCustomCommand(ctx, name)

    @command.command(aliases=["exec"])
    async def run(self, ctx, name: str, argument: str = None):
        """Run a custom command"""
        return await self.execCustomCommand(ctx, name)

    @command.command(aliases=["+", "create"])
    async def add(self, ctx, name: str, *, content: str):
        """Add new command"""

        # Check if command already exists
        rows = await self.db.fetch_all("""
            SELECT *
            FROM commands
            INNER JOIN commands_lookup ON
                commands.id = commands_lookup.cmdId
            WHERE
                commands_lookup.name = :name
        """, values={"name": name})
        if rows:
            return await ctx.try_reply("A command/alias called `{}` already exists!".format(name))
        
        # Adding command to database
        async with self.db.transaction():
            lastInsert = await self.db.execute(
                dbQuery.insertToCommands,
                values={
                    "name": name,
                    "content": content,
                    "ownerId": ctx.author.id,
                    "createdAt": dt.datetime.utcnow().timestamp(),
                }
            )
            lastLastInsert = await self.db.execute(
                dbQuery.insertToCommandsLookup,
                values={
                    "cmdId": lastInsert,
                    "name": name,
                    "guildId": ctx.guild.id,
                }
            )
            if lastInsert and lastLastInsert:
                await ctx.send("{} has been created".format(name))

    @command.command(aliases=["/"])
    async def alias(self, ctx, alias, command):
        """Create alias for a command"""
        pass

    @command.command(aliases=["&"])
    async def edit(self, ctx, name, *, content):
        """Edit existing command"""
        pass

    @command.command(aliases=["-", "rm"])
    async def remove(self, ctx, name):
        """Remove a command"""
        pass

    @command.command()
    async def disable(self, ctx, name):
        """Disable a command"""
        # This will work for both built-in and user-made commands
        pass

    @command.command()
    async def enable(self, ctx, name):
        """Enable a command"""
        # This will work for both built-in and user-made commands
        pass

    @command.command(aliases=["?"])
    async def info(self, ctx, name):
        """Show information about a command"""
        # Executes {prefix}help {name} if its built-in command
        pass

    @commands.command()
    async def source(self, ctx):
        """Get link to my source code."""
        await ctx.send("My source code: {}".format(links["Source Code"]))

    @commands.command(aliases=["bi", "about"])
    async def botinfo(self, ctx):
        """Information about me."""

        # Z3R0 Banner
        f = discord.File("./assets/img/banner.png", filename="banner.png")

        e = discord.Embed(
            description=self.bot.description
            + "\n\nThis bot is licensed under **{}**.".format(license),
            timestamp=ctx.message.created_at,
            colour=self.bot.colour,
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        e.set_image(url="attachment://banner.png")
        e.add_field(name="Author", value=author)
        e.add_field(
            name="Library",
            value="[`zidiscord.py`](https://github.com/null2264/discord.py) - `v{}`".format(
                discord.__version__
            ),
        )
        e.add_field(name="Version", value=version)
        e.add_field(
            name="Links",
            value="\n".join(
                [
                    "- [{}]({})".format(k, v) if v else "- {}".format(k)
                    for k, v in links.items()
                ]
            ),
            inline=False,
        )
        await ctx.try_reply(file=f, embed=e)

    @commands.command()
    async def stats(self, ctx):
        uptime = dt.datetime.utcnow() - self.bot.uptime
        e = discord.Embed(
            timestamp=ctx.message.created_at,
            colour=self.bot.colour,
        )
        e.set_author(name=ctx.bot.user.name + "'s stats", icon_url=ctx.bot.user.avatar_url)
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        e.add_field(name="🕙 | Uptime", value=humanize.precisedelta(uptime))
        await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Meta(bot))
