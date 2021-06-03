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


class CustomCommand:
    """Object for custom command."""

    __slots__ = (
        "id",
        "name",
        "invokedName",
        "description",
        "category",
        "content",
        "aliases",
    )

    def __init__(self, id, name, category, **kwargs):
        self.id = id

        self.name = name
        # Incase its invoked using its alias
        self.invokedName = kwargs.pop("invokedName", name)

        self.description = kwargs.pop("description", None) or "No description."
        self.content = kwargs.pop("content", "NULL")
        self.category = category
        self.aliases = kwargs.pop("aliases", [])

        # - Convert 1 and 0 to True and False
        # No longer used, replaced by invokedName
        # self.isAlias = True if isAlias else False

    def __str__(self):
        return self.name


async def getCustomCommand(ctx, db, command):
    try:
        _id, name = await db.fetch_one(
            dbQuery.getCommandId, values={"name": command, "guildId": ctx.guild.id}
        )
    except TypeError:
        # No command found
        raise CCommandNotFound(command)

    result = await db.fetch_all(dbQuery.getCommandContent, values={"id": _id})
    firstRes = result[0]
    return CustomCommand(
        id=_id,
        content=firstRes[0],
        name=firstRes[1],
        invokedName=name,
        category=firstRes[2],
        description=firstRes[3],
        aliases=[row[2] for row in result if row[2] != row[1]],
    )


async def getCustomCommands(db, guildId):
    """Get all custom commands from guild id."""

    # cmd = {
    #     "command_id": {
    #         "name": "command",
    #         "description": null,
    #         "category": null,
    #         "aliases": ["alias", ...]
    #     }
    # }

    cmds = {}
    rows = await db.fetch_all(dbQuery.getCommands, values={"guildId": guildId})
    for row in rows:
        isAlias = row[1] != row[2]

        if row[0] not in cmds:
            cmds[row[0]] = {}

        if not isAlias:
            # If its not an alias
            cmds[row[0]] = {
                "name": row[2],  # "real" name
                "description": row[3],
                "category": row[4],
            }
        else:
            try:
                cmds[row[0]]["aliases"] += [row[1]]
            except KeyError:
                cmds[row[0]]["aliases"] = [row[1]]

    return [
        CustomCommand(
            id=k,
            name=v["name"],
            description=v["description"],
            category=v["category"],
            aliases=v.get("aliases", []),
        )
        for k, v in cmds.items()
    ]


class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context

        # Add custom commands to mapping
        ccs = await getCustomCommands(ctx.db, ctx.guild.id)
        for cmd in ccs:
            mapping[cmd.category] += [cmd]

        dest = self.get_destination()
        e = discord.Embed(
            description=infoQuote.info("`()` : **Required**\n`[]` : **Optional**"),
            colour=ctx.bot.colour,
        )
        e.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)

        unsorted = mapping.pop(None)
        for cog, commands in sorted(mapping.items(), key=lambda c: c[0].qualified_name):
            # TODO: filter commands, only show command that can be executed
            if not commands:
                continue
            e.add_field(
                name=cog.qualified_name,
                value=", ".join(
                    [f"`{cmd.name}`" for cmd in sorted(commands, key=lambda c: c.name)]
                ),
            )
        e.add_field(
            name="Unsorted",
            value=", ".join(
                [f"`{cmd.name}`" for cmd in sorted(unsorted, key=lambda c: c.name)]
            ),
        )
        await dest.send(embed=e)


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
        result = await getCustomCommand(ctx, self.db, command)
        async with self.db.transaction():
            # Increment uses
            await self.db.execute(dbQuery.incrCommandUsage, values={"id": result.id})
            return await ctx.send(result.content)

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
        rows = await self.db.fetch_all(
            """
            SELECT *
            FROM commands
            INNER JOIN commands_lookup ON
                commands.id = commands_lookup.cmdId
            WHERE
                commands_lookup.name = :name AND commands_lookup.guildId = :guildId
        """,
            values={"name": name, "guildId": ctx.guild.id},
        )
        if rows:
            return await ctx.try_reply(
                "A command/alias called `{}` already exists!".format(name)
            )

        # Adding command to database
        async with self.db.transaction():
            lastInsert = await self.db.execute(
                dbQuery.insertToCommands,
                values={
                    "name": name,
                    "content": content,
                    "ownerId": ctx.author.id,
                    "createdAt": dt.datetime.utcnow().timestamp(),
                },
            )
            lastLastInsert = await self.db.execute(
                dbQuery.insertToCommandsLookup,
                values={
                    "cmdId": lastInsert,
                    "name": name,
                    "guildId": ctx.guild.id,
                    "isAlias": 0,
                },
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
        e.set_author(
            name=ctx.bot.user.name + "'s stats", icon_url=ctx.bot.user.avatar_url
        )
        e.set_footer(
            text="Requested by {}".format(str(ctx.author)),
            icon_url=ctx.author.avatar_url,
        )
        e.add_field(
            name="🕙 | Uptime", value=humanize.precisedelta(uptime), inline=False
        )
        e.add_field(
            name="`>_` | Command Usage (This session)",
            value="{} commands".format(self.bot.commandUsage),
            inline=False,
        )
        await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Meta(bot))
