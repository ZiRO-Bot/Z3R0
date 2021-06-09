"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import discord
import datetime as dt
import humanize
import re
import TagScriptEngine as tse


from core.errors import CCommandNotFound, CCommandAlreadyExists
from core.mixin import CogMixin
from core.objects import CustomCommand
from exts.utils import dbQuery, infoQuote, tseBlocks
from exts.utils.format import CMDName, ZEmbed
from discord.ext import commands


GIST_REGEX = re.compile(
    r"http(?:s)?:\/\/gist\.github(?:usercontent)?\.com\/.*\/(\S*)(?:\/)?"
)
PASTEBIN_REGEX = re.compile(r"http(?:s)?:\/\/pastebin.com\/(?:raw\/)?(\S*)")


async def getCustomCommand(ctx, db, command):
    """Get custom command from database."""
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
        description=firstRes[3],
        category=firstRes[4],
        aliases=[row[2] for row in result if row[2] != row[1]],
        uses=firstRes[5] + 1,
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
    # Create temporary dict
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

        dest = self.get_destination()

        e = ZEmbed(
            description=infoQuote.info(
                "- () : Required Argument\n"
                + "+ [] : Optional Argument\n"
                + "\nDon't literally type `[]`, `()` or `|`!",
                codeBlock=True,
            ),
        )
        e.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        e.set_footer(
            text="Use `{}help [category|command]` for more information".format(
                ctx.prefix
            )
        )

        unsorted = mapping.pop(None)
        sortedCog = sorted(mapping.keys(), key=lambda c: c.qualified_name)

        ignored = ["ErrorHandler"]
        e.add_field(
            name="Categories",
            value="\n".join(
                [
                    "• {} **{}**".format(getattr(cog, "icon", "❓"), cog.qualified_name)
                    for cog in sortedCog
                    if cog.qualified_name not in ignored
                ]
                + ["• ❓ **Unsorted**"]
            ),
        )

        return await dest.send(embed=e)

        # TODO: Move these stuff below to send_cog_help
        # Add custom commands to mapping
        ccs = await getCustomCommands(ctx.db, ctx.guild.id)
        for cmd in ccs:
            mapping[cmd.category] += [cmd]

        unsorted = mapping.pop(None)
        ignored = ["ErrorHandler"]
        for cog, commands in sorted(mapping.items(), key=lambda c: c[0].qualified_name):
            # TODO: filter commands, only show command that can be executed
            if cog.qualified_name in ignored:
                continue
            value = (
                ", ".join(
                    [f"`{cmd.name}`" for cmd in sorted(commands, key=lambda c: c.name)]
                )
                if commands
                else "No commands."
            )
            e.add_field(
                name=cog.qualified_name,
                value=value,
            )
        value = (
            ", ".join(
                [f"`{cmd.name}`" for cmd in sorted(unsorted, key=lambda c: c.name)]
            )
            if unsorted
            else "No commands."
        )
        e.add_field(
            name="Unsorted",
            value=value,
        )
        await dest.send(embed=e)


class Meta(commands.Cog, CogMixin):
    """Bot-related commands."""

    icon = "🤖"

    def __init__(self, bot):
        super().__init__(bot)
        # Replace default help menu with custom one
        self._original_help_command = bot.help_command
        self.bot.help_command = CustomHelp()
        self.bot.help_command.cog = self

        # TSE stuff
        blocks = [
            tse.LooseVariableGetterBlock(),
            tse.RandomBlock(),
            tse.AssignmentBlock(),
            tse.RequireBlock(),
            tse.EmbedBlock(),
            tse.RedirectBlock(),
            tseBlocks.SilentBlock(),
            tseBlocks.ReactBlock(),
            tseBlocks.ReactUBlock(),
        ]
        self.engine = tse.Interpreter(blocks)

        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        async with self.db.transaction():
            # commands database table
            await self.db.execute(dbQuery.createCommandsTable)
            # commands_lookup database table
            await self.db.execute(dbQuery.createCommandsLookupTable)

    async def reactsToMessage(self, message: discord.Message, reactions: list = []):
        """Simple loop to react to a message."""
        for reaction in reactions:
            await asyncio.sleep(0.5)
            try:
                await message.add_reaction(reaction)
            except:
                continue

    def processTag(self, ctx, cmd: CustomCommand):
        """Process tags from CC's content with TSE."""
        author = tse.MemberAdapter(ctx.author)
        content = cmd.content
        # TODO: Make target uses custom command arguments instead
        target = (
            tse.MemberAdapter(ctx.message.mentions[0])
            if ctx.message.mentions
            else author
        )
        channel = tse.ChannelAdapter(ctx.channel)
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
            "unix": tse.IntAdapter(int(dt.datetime.utcnow().timestamp())),
            "prefix": ctx.prefix,
            "uses": tse.IntAdapter(cmd.uses),
        }
        if ctx.guild:
            guild = tse.GuildAdapter(ctx.guild)
            seed.update(guild=guild, server=guild)
        return self.engine.process(content, seed)

    async def execCustomCommand(self, ctx, command):
        cmd = await getCustomCommand(ctx, self.db, command)
        async with self.db.transaction():
            # Increment uses
            await self.db.execute(dbQuery.incrCommandUsage, values={"id": cmd.id})
            result = self.processTag(ctx, cmd)
            embed = result.actions.get("embed")

            dest = result.actions.get("target")
            action = ctx.send
            if dest:
                if dest == "reply":
                    action = ctx.try_reply
                if dest == "dm":
                    action = ctx.author.send

            msg = await action(
                result.body or ("\u200b" if not embed else ""), embed=embed
            )
            react = result.actions.get("react")
            reactu = result.actions.get("reactu")
            if reactu:
                self.bot.loop.create_task(self.reactsToMessage(ctx.message, reactu))
            if react:
                self.bot.loop.create_task(self.reactsToMessage(msg, react))

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
    # TODO: Separate tags from custom command
    @commands.group(aliases=["cmd", "tag", "script"], invoke_without_command=True)
    async def command(self, ctx, name: CMDName, argument: str = None):
        """Manage commands"""
        return await self.execCustomCommand(ctx, name)

    @command.command(aliases=["exec"])
    async def run(self, ctx, name: CMDName, argument: str = None):
        """Run a custom command"""
        return await self.execCustomCommand(ctx, name)

    async def addCmd(self, ctx, name: str, content: str, **kwargs):
        """Add cmd to database"""
        async with self.db.transaction():
            lastInsert = await self.db.execute(
                dbQuery.insertToCommands,
                values={
                    "name": name,
                    "content": content,
                    "ownerId": ctx.author.id,
                    "createdAt": dt.datetime.utcnow().timestamp(),
                    "type": kwargs.get("type", "text"),
                    "url": kwargs.get("url", None),
                },
            )
            lastLastInsert = await self.db.execute(
                dbQuery.insertToCommandsLookup,
                values={
                    "cmdId": lastInsert,
                    "name": name,
                    "guildId": ctx.guild.id,
                },
            )
            return lastInsert, lastLastInsert
        return None, None

    async def isCmdExist(self, ctx, name: str):
        """Check if command already exists"""
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
            raise CCommandAlreadyExists(name)

    def getValidLink(self, url):
        # Link will either be None, pastebin, or gist
        link = None

        url = url.rstrip("/")

        # Regex stuff
        # TODO: Find better way of finding "valid" url
        group = GIST_REGEX.fullmatch(str(url))
        if group:
            if group.group(1) == "raw":
                link = group.group(0)
            else:
                link = group.group(0) + "/raw"
        else:
            group = PASTEBIN_REGEX.fullmatch(str(url))
            if not group:
                raise commands.BadArgument
            link = "https://pastebin.com/raw/" + group.group(1)
        return link

    @command.command(name="import", aliases=["++"])
    @modeCheck()
    async def _import(self, ctx, name: CMDName, *, url: str):
        """Import command from pastebin/github gist"""
        # NOTE: This command will only support pastebin and gist.github,
        # maybe also hastebin.
        link = self.getValidLink(url)

        # Check if command already exists
        await self.isCmdExist(ctx, name)

        request = await self.bot.session.get(link)
        content = await request.text()

        lastInsert, lastLastInsert = await self.addCmd(
            ctx, name, content, type="import", url=url
        )
        if lastInsert and lastLastInsert:
            await ctx.send("`{}` has been imported (Source: <{}>)".format(name, link))

    @command.command(name="update-url", aliases=["&u"])
    async def update_url(self, ctx, name: CMDName, url: str):
        """Update imported command's source url"""
        link = self.getValidLink(url)

    @command.command(aliases=["&&"])
    async def update(self, ctx, name: CMDName):
        """Update imported command"""

    @command.command(name="add", aliases=["+", "create"])
    @modeCheck()
    async def _add(self, ctx, name: CMDName, *, content: str):
        """Add new command"""
        # Check if command already exists
        await self.isCmdExist(ctx, name)

        # Adding command to database
        lastInsert, lastLastInsert = await self.addCmd(ctx, name, content)
        if lastInsert and lastLastInsert:
            await ctx.send("`{}` has been created".format(name))

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
        command = await getCustomCommand(ctx, ctx.db, name)
        isAlias = name in command.aliases
        if isAlias:
            async with ctx.db.transaction():
                await ctx.db.execute(
                    dbQuery.deleteCommandAlias,
                    values={"name": name, "guildId": ctx.guild.id},
                )
        else:
            # Aliases will be deleted automatically
            # NOTE TO DEVS: You must have `ON DELETE CASCADE`
            async with ctx.db.transaction():
                await ctx.db.execute(dbQuery.deleteCommand, values={"id": command.id})
        # TODO: Adjust removed message
        return await ctx.send("{} has been removed".format(name))

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

    @commands.command(aliases=["botinfo", "bi"])
    async def about(self, ctx):
        """Information about me."""

        # Z3R0 Banner
        f = discord.File("./assets/img/banner.png", filename="banner.png")

        e = ZEmbed.default(
            ctx,
            description=self.bot.description
            + "\n\nThis bot is licensed under **{}**.".format(ctx.bot.license),
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        e.set_image(url="attachment://banner.png")
        e.add_field(name="Author", value=ctx.bot.author)
        e.add_field(
            name="Library",
            value="[`zidiscord.py`](https://github.com/null2264/discord.py) - `v{}`".format(
                discord.__version__
            ),
        )
        e.add_field(name="Version", value=ctx.bot.version)
        e.add_field(
            name="Links",
            value="\n".join(
                [
                    "- [{}]({})".format(k, v) if v else "- {}".format(k)
                    for k, v in ctx.bot.links.items()
                ]
            ),
            inline=False,
        )
        await ctx.try_reply(file=f, embed=e)

    @commands.command()
    async def stats(self, ctx):
        uptime = dt.datetime.utcnow() - self.bot.uptime
        e = ZEmbed.default(ctx)
        e.set_author(
            name=ctx.bot.user.name + "'s stats", icon_url=ctx.bot.user.avatar_url
        )
        e.add_field(
            name="🕙 | Uptime", value=humanize.precisedelta(uptime), inline=False
        )
        e.add_field(
            name="`>_` | Command Usage (This session)",
            value="{} commands ({} custom commands)".format(
                self.bot.commandUsage, self.bot.customCommandUsage
            ),
            inline=False,
        )
        await ctx.try_reply(embed=e)


def setup(bot):
    bot.add_cog(Meta(bot))
