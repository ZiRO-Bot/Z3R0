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
from exts.utils.format import CMDName
from discord.ext import commands


class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        destination = self.get_destination()
        e = discord.Embed(
            description=infoQuote.info(
                "`()`: **Required**\n`[]`: **Optional**"
            ).replace("   ", ""),
            colour=ctx.bot.colour,
        )
        e.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        e.add_field(name="Commands", value="Placeholder")
        await destination.send(embed=e)


# --- NOTE: Edit these stuff to your liking
AUTHOR = "ZiRO2264#4572"
VERSION = "`v3.0.O` - `overhaul`"
LINKS = {
    "Documentation (Coming Soon)": "",
    "Source Code": "https://github.com/ZiRO-Bot/ziBot",
    "Support Server": "https://discord.gg/sP9xRy6",
}
LICENSE = "Mozilla Public License, v. 2.0"
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

    def modeCheck():
        """Check for custom command's modes."""
        async def pred(ctx):
            return True
            # return await check_permissions(ctx, perms, check=check)

        return commands.check(pred)

    # TODO: Adds custom check with usage limit (
    #     0: Only mods,
    #     1: Partial (Can only add/edit/remove their own command),
    #     2: Full (Can do anything to any existing command in the guild)
    # )
    # Also separate tags from custom command later on
    @commands.group(aliases=["cmd", "tag", "script"], invoke_without_command=True)
    async def command(self, ctx, name: CMDName, argument: str = None):
        """Manage commands"""
        return await self.execCustomCommand(ctx, name)

    @command.command(aliases=["exec"])
    async def run(self, ctx, name: CMDName, argument: str = None):
        """Run a custom command"""
        return await self.execCustomCommand(ctx, name)

    @command.command(aliases=["+", "create"])
    @modeCheck()
    async def add(self, ctx, name: CMDName, *, content: str):
        """Add new command"""

        # Check if command already exists
        rows = await self.db.fetch_all("""
            SELECT *
            FROM commands
            INNER JOIN commands_lookup ON
                commands.id = commands_lookup.cmdId
            WHERE
                commands_lookup.name = :name AND commands_lookup.guildId = :guildId
        """, values={"name": name, "guildId": ctx.guild.id})
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
    @modeCheck()
    async def alias(self, ctx, alias: CMDName, command):
        """Create alias for a command"""
        pass

    @command.command(aliases=["&"])
    @modeCheck()
    async def edit(self, ctx, name: CMDName, *, content):
        """Edit existing command"""
        pass

    @command.command(aliases=["-", "rm"])
    @modeCheck()
    async def remove(self, ctx, name: CMDName):
        """Remove a command"""
        pass

    @command.command()
    @modeCheck()
    async def disable(self, ctx, name: CMDName):
        """Disable a command"""
        # This will work for both built-in and user-made commands
        # NOTE: Only mods can enable/disable built-in command
        pass

    @command.command()
    @modeCheck()
    async def enable(self, ctx, name: CMDName):
        """Enable a command"""
        # This will work for both built-in and user-made commands
        # NOTE: Only mods can enable/disable built-in command
        pass

    @command.command(aliases=["?"])
    async def info(self, ctx, name: CMDName):
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
        e.add_field(name="Author", value=AUTHOR)
        e.add_field(
            name="Library",
            value="[`zidiscord.py`](https://github.com/null2264/discord.py) - `v{}`".format(
                discord.__version__
            ),
        )
        e.add_field(name="Version", value=VERSION)
        e.add_field(
            name="Links",
            value="\n".join(
                [
                    "- [{}]({})".format(k, v) if v else "- {}".format(k)
                    for k, v in LINKS.items()
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
