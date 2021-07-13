"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import asyncio
import difflib
import discord
import humanize
import re
import shlex
import TagScriptEngine as tse
import time


from core import checks
from core.errors import (
    CCommandNotFound,
    CCommandAlreadyExists,
    CCommandNotInGuild,
    CCommandNoPerm,
    CCommandDisabled,
)
from core.menus import ZMenu
from core.mixin import CogMixin
from core.objects import CustomCommand
from exts.utils import dbQuery, infoQuote, tseBlocks
from exts.utils.cache import CacheListProperty, CacheUniqueViolation, CacheError
from exts.utils.format import (
    CMDName,
    ZEmbed,
    cleanifyPrefix,
    formatCmd,
    formatCmdParams,
)
from exts.utils.other import reactsToMessage, ArgumentParser, utcnow
from discord.ext import commands, menus


GIST_REGEX = re.compile(
    r"http(?:s)?:\/\/gist\.github(?:usercontent)?\.com\/.*\/(\S*)(?:\/)?"
)
PASTEBIN_REGEX = re.compile(r"http(?:s)?:\/\/pastebin.com\/(?:raw\/)?(\S*)")


DIFFER = difflib.Differ()


class PrefixesPageSource(menus.ListPageSource):
    def __init__(self, ctx, prefixes):
        self.prefixes = prefixes
        self.ctx = ctx

        super().__init__(prefixes, per_page=6)

    async def format_page(self, menu: menus.MenuPages, prefixes: list):
        ctx = self.ctx

        e = ZEmbed(
            title="{} Prefixes".format(ctx.guild), description="**Custom Prefixes**:\n"
        )

        if menu.current_page == 0:
            prefixes.pop(0)
            prefixes.pop(0)
            e.description = (
                "**Default Prefixes**: `{}` or `{} `\n\n**Custom Prefixes**:\n".format(
                    ctx.bot.defPrefix, cleanifyPrefix(ctx.bot, ctx.me.mention)
                )
            )
        e.description += (
            "\n".join([f"• `{cleanifyPrefix(ctx.bot, p)}`" for p in prefixes])
            or "No custom prefix."
        )
        return e


async def getCustomCommand(ctx, command):
    """Get custom command from database."""
    db = ctx.db
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
        url=firstRes[6],
        owner=firstRes[7],
        enabled=firstRes[8],
    )


async def getCustomCommands(db, guildId, category: str = None):
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

    query = dbQuery.getCommands
    values = {"guildId": guildId}
    if category:
        query += " AND commands.category = :category"
        values["category"] = category.lower()
    rows = await db.fetch_all(query, values=values)

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
                "owner": row[5],
                "enabled": row[6],
            }
        else:
            try:
                cmds[row[0]]["aliases"] += [row[1]]
            except KeyError:
                cmds[row[0]]["aliases"] = [row[1]]

    return [CustomCommand(id=k, **v) for k, v in cmds.items()]


async def formatCommandInfo(prefix, command):
    """Format command help"""
    e = ZEmbed(
        title=formatCmd(prefix, command),
        description="**Aliases**: `{}`\n".format(
            ", ".join(command.aliases) if command.aliases else "No alias"
        )
        + (command.description or command.brief or "No description"),
    )

    if not isinstance(command, CustomCommand):
        optionDict: dict = command.raw.get("flags")
        if optionDict:
            optionStr = []
            for key, value in optionDict.items():
                name = (
                    " | ".join([f"`{i}`" for i in key])
                    if isinstance(key, tuple)
                    else key
                )
                optionStr.append(f"{name}: {value}")
            e.add_field(name="Options", value="\n".join(optionStr), inline=False)

        examples = getattr(command, "example", None)
        if examples:
            e.add_field(
                name="Example",
                value="\n".join([f"> `{prefix}{x}`" for x in examples]),
            )

    if isinstance(command, commands.Group):
        subcmds = sorted(command.commands, key=lambda c: c.name)
        if subcmds:
            e.add_field(
                name="Subcommands",
                value="\n".join([f"> `{formatCmd(prefix, cmd)}`" for cmd in subcmds]),
            )

    return e


class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context

        e = ZEmbed(
            description=infoQuote.info(
                "- () : Required Argument\n"
                + "+ [] : Optional Argument\n"
                + "\nDon't literally type `[]`, `()` or `|`!",
                codeBlock=True,
            )
            + " | ".join("[{}]({})".format(k, v) for k, v in ctx.bot.links.items()),
        )
        e.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        e.set_footer(
            text="Use `{}help [category|command]` for more information".format(
                ctx.prefix
            )
        )

        unsorted = mapping.pop(None)
        sortedCog = sorted(mapping.keys(), key=lambda c: c.qualified_name)

        ignored = ("EventHandler", "Jishaku", "NSFW")
        e.add_field(
            name="Categories",
            value="\n".join(
                [
                    "• {} **{}**".format(getattr(cog, "icon", "❓"), cog.qualified_name)
                    for cog in sortedCog
                    if cog.qualified_name not in ignored
                ]
            ),
        )
        e.add_field(name="News | Updated: {}".format("?"), value="Nothing.")

        return await ctx.try_reply(embed=e)

    async def send_cog_help(self, cog):
        ctx = self.context

        # Getting all the commands
        filtered = await self.filter_commands(cog.get_commands())
        ccs = await getCustomCommands(ctx.db, ctx.guild.id, cog.qualified_name)
        for cmd in ccs:
            filtered.append(cmd)
        filtered = sorted(filtered, key=lambda c: c.name)

        desc = infoQuote.info(
            "- 'ᶜ': Custom Command\n+ 'ᵍ': Group (have subcommand(s))",
            codeBlock=True,
        )

        e = ZEmbed(
            title=f"{getattr(cog, 'icon', '❓')} | Category: {cog.qualified_name}",
            description=desc,
        )
        for cmd in filtered:
            name = cmd.name
            if isinstance(cmd, CustomCommand):
                name += "ᶜ"
            if isinstance(cmd, commands.Group):
                name += "ᵍ"

            e.add_field(
                name=name,
                value="> " + (cmd.brief or "No description"),
            )
        e.set_footer(
            text="Use `{}command info command-name` to check custom command's information".format(
                ctx.clean_prefix
            )
        )
        await ctx.try_reply(embed=e)

    async def command_not_found(self, string):
        ctx = self.context
        try:
            command = await getCustomCommand(ctx, string)
            await self.send_command_help(command)
            return command
        except:
            return "No command called `{}` found.".format(string)

    async def send_error_message(self, error):
        if isinstance(error, CustomCommand):
            return
        await self.context.try_reply(error)

    # TODO: Add aliases to group and command help
    async def send_command_help(self, command):
        ctx = self.context

        e = await formatCommandInfo(ctx.clean_prefix, command)

        await ctx.try_reply(embed=e)

    async def send_group_help(self, group):
        ctx = self.context

        e = await formatCommandInfo(ctx.clean_prefix, group)

        await ctx.try_reply(embed=e)

    # TODO: Override command_callback to get custom command properly, flags,
    # filter, etc
    # async def command_callback(self, ctx, *, command=None):


class Meta(commands.Cog, CogMixin):
    """Bot-related commands."""

    icon = "🤖"
    cc = True

    def __init__(self, bot):
        super().__init__(bot)
        # Replace default help menu with custom one
        self._original_help_command = bot.help_command
        self.bot.help_command = CustomHelp()
        self.bot.help_command.cog = self
        self.bot.cache.add(
            "disabled",
            cls=CacheListProperty,
        )

        # TSE stuff
        blocks = [
            tse.AssignmentBlock(),
            tse.EmbedBlock(),
            tse.LooseVariableGetterBlock(),
            tse.RedirectBlock(),
            tse.RequireBlock(),
            tseBlocks.RandomBlock(),
            tseBlocks.ReactBlock(),
            tseBlocks.ReactUBlock(),
            tseBlocks.SilentBlock(),
        ]
        self.engine = tse.Interpreter(blocks)

        self.bot.loop.create_task(self.asyncInit())

    async def asyncInit(self):
        async with self.db.transaction():
            # commands database table
            await self.db.execute(dbQuery.createCommandsTable)
            # commands_lookup database table
            await self.db.execute(dbQuery.createCommandsLookupTable)

    def formatCmdName(self, command):
        commands = []

        parent = command.parent
        while parent is not None:
            commands.append(parent.name)
            parent = parent.parent
        return " ".join(reversed([command.name] + commands))

    async def getDisabledCommands(self, ctx, guildId):
        if self.bot.cache.disabled.get(guildId) is None:
            dbDisabled = await ctx.db.fetch_all(
                "SELECT command FROM disabled WHERE guildId=:id", values={"id": guildId}
            )
            try:
                self.bot.cache.disabled.extend(guildId, [c[0] for c in dbDisabled])
            except ValueError:
                return []
        return self.bot.cache.disabled.get(guildId, [])

    async def bot_check(self, ctx):
        """Global check"""
        disableCmds = await self.getDisabledCommands(ctx, ctx.guild.id)
        cmdName = self.formatCmdName(ctx.command)
        if cmdName in disableCmds:
            if not ctx.author.guild_permissions.manage_guild:
                raise commands.DisabledCommand
        return True

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
            "unix": tse.IntAdapter(int(utcnow().timestamp())),
            "prefix": ctx.prefix,
            "uses": tse.IntAdapter(cmd.uses),
        }
        if ctx.guild:
            guild = tse.GuildAdapter(ctx.guild)
            seed.update(guild=guild, server=guild)
        return self.engine.process(content, seed)

    async def execCustomCommand(self, ctx, command, raw: bool = False):
        if not ctx.guild:
            raise CCommandNotInGuild
        cmd = await getCustomCommand(ctx, command)
        if not cmd.enabled:
            raise CCommandDisabled
        if raw:
            content = discord.utils.escape_markdown(cmd.content)
            return await ctx.try_reply(content)

        async with ctx.db.transaction():
            # Increment uses
            await ctx.db.execute(dbQuery.incrCommandUsage, values={"id": cmd.id})
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
                self.bot.loop.create_task(reactsToMessage(ctx.message, reactu))
            if react:
                self.bot.loop.create_task(reactsToMessage(msg, react))

    async def ccModeCheck(
        self, ctx, _type: str = "manage", command: CustomCommand = None
    ):
        """Check for custom command's modes."""
        # 0: Only mods,
        # 1: Partial (Can add but only able to manage their own command),
        # 2: Full (Anarchy mode)

        # Getting config
        mode = await self.bot.getGuildConfig(ctx.guild.id, "ccMode")

        isMod = await checks.isMod(ctx)
        if _type == "manage":
            # Manage = edit, update, update-url, etc
            if not command:
                # How?
                return False

            isCmdOwner = ctx.author.id == command.owner
            return {
                0: isMod,
                1: isCmdOwner or isMod,
                2: True,
            }.get(mode, False)
        elif _type == "add":
            return isMod if mode == 0 else True
        # Fallback to false
        return False

    # TODO: Separate tags from custom command
    @commands.guild_only()
    @commands.group(
        aliases=["cmd", "tag", "script"],
        invoke_without_command=True,
        brief="Manage commands",
        description=(
            "Manage commands\n\n**NOTE**: Custom Commands only available for "
            "guilds/servers!"
        ),
    )
    async def command(self, ctx, name: CMDName, argument: str = None):
        return await self.execCustomCommand(ctx, name)

    @command.command(aliases=["exec", "execute"], brief="Execute a custom command")
    async def run(self, ctx, name: CMDName, argument: str = None):
        return await self.execCustomCommand(ctx, name)

    @command.command(brief="Get raw content of a custom command")
    async def raw(self, ctx, name: CMDName):
        return await self.execCustomCommand(ctx, name, raw=True)

    async def addCmd(self, ctx, name: str, content: str, **kwargs):
        """Add cmd to database"""
        async with ctx.db.transaction():
            lastInsert = await ctx.db.execute(
                dbQuery.insertToCommands,
                values={
                    "name": name,
                    "content": content,
                    "ownerId": ctx.author.id,
                    "createdAt": utcnow().timestamp(),
                    "type": kwargs.get("type", "text"),
                    "url": kwargs.get("url", None),
                },
            )
            lastLastInsert = await ctx.db.execute(
                dbQuery.insertToCommandsLookup,
                values={
                    "cmdId": lastInsert,
                    "name": name,
                    "guildId": ctx.guild.id,
                },
            )
            return lastInsert, lastLastInsert
        return (None,) * 2

    async def isCmdExist(self, ctx, name: str):
        """Check if command already exists"""
        rows = await ctx.db.fetch_all(
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
        # TODO: Find better way to parse valid link
        # TODO: Add support for hastebin and mystb.in
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
                raise commands.BadArgument("<{}> is not a valid url!".format(url))
            link = "https://pastebin.com/raw/" + group.group(1)
        return link

    @command.command(
        name="import",
        aliases=["++"],
        brief="Import a custom command from pastebin/gist.github",
        example=(
            "command import pastebin-cmd https://pastebin.com/ZxvGqEAs",
            "command ++ gist "
            "https://gist.github.com/null2264/87c89d2b5e2453529e29c2cae3b57729",
        ),
    )
    async def _import(self, ctx, name: CMDName, *, url: str):
        perm = await self.ccModeCheck(ctx, "add")
        if not perm:
            raise CCommandNoPerm

        # NOTE: This command will only support pastebin and gist.github,
        # maybe also hastebin.
        try:
            link = self.getValidLink(url)
        except commands.BadArgument as exc:
            return await ctx.try_reply(str(exc))

        # Check if command already exists
        await self.isCmdExist(ctx, name)

        content = None
        async with self.bot.session.get(link) as request:
            content = await request.text()

        lastInsert, lastLastInsert = await self.addCmd(
            ctx,
            name,
            content or "`ERROR`: Failed to retrieve command",
            type="import",
            url=link,
        )
        if lastInsert and lastLastInsert:
            await ctx.try_reply(
                "`{}` has been imported (Source: <{}>)".format(name, url)
            )

    @command.command(
        name="update-url",
        aliases=["&u", "set-url"],
        brief="Update imported command's source url",
    )
    async def update_url(self, ctx, name: CMDName, url: str):
        # NOTE: Can only be run by cmd owner or guild mods/owner
        command = await getCustomCommand(ctx, name)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if not command.url:
            # Incase someone try to update `text` command
            return await ctx.try_reply(
                "`{}` is not imported command! Please use '{}command edit' instead!".format(
                    name, ctx.prefix
                )
            )
        try:
            link = self.getValidLink(url)
        except commands.BadArgument as exc:
            return await ctx.try_reply(str(exc))

        if link == command.url:
            return await ctx.try_reply("Nothing changed.")

        async with ctx.db.transaction():
            await ctx.db.execute(
                dbQuery.updateCommandUrl,
                values={"url": link, "id": command.id},
            )
            return await ctx.try_reply(
                "`{}` url has been set to <{}>.".format(name, url)
                + "\nPlease do `{}command update {}` to update the content!".format(
                    ctx.prefix, name
                )
            )

    async def updateCommandContent(self, ctx, command: CustomCommand, content):
        """Update command's content"""
        async with ctx.db.transaction():
            await ctx.db.execute(
                dbQuery.updateCommandContent,
                values={"content": content, "id": command.id},
            )
            return True
        return False

    @command.command(
        aliases=["&&", "pull"],
        brief="Update imported command's content",
    )
    async def update(self, ctx, name: CMDName):
        # NOTE: Can only be run by cmd owner or guild mods/owner

        # For both checking if command exists and
        # getting its content for comparation later on
        command = await getCustomCommand(ctx, name)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if not command.url:
            # Incase someone try to update `text` command
            return await ctx.try_reply(
                "`{}` is not imported command! Please use '{}command edit' instead!".format(
                    name, ctx.prefix
                )
            )

        content = None
        async with self.bot.session.get(command.url) as request:
            content = await request.text()

        # Compare and get changes
        addition = 0
        deletion = 0
        for changes in DIFFER.compare(command.content, content or ""):
            if changes.startswith("- "):
                deletion += 1
            if changes.startswith("+ "):
                addition += 1
        if not addition and not deletion:
            # Nothing changed, so let's just send a message
            return await ctx.try_reply(
                "Already up to date."
                + "\n[**Note**]: It takes awhile for the site to be updated!"
            )

        update = await self.updateCommandContent(ctx, command, content)
        if update:
            return await ctx.try_reply(
                "Command `{}` has been update\n".format(name)
                + "`[+]` {} Additions\n".format(addition)
                + "`[-]` {} Deletions".format(deletion)
            )

    @command.command(
        name="add",
        aliases=["+", "create"],
        brief="Create a new custom command",
        example=(
            "command add example-cmd Just an example",
            "cmd + hello Hello World!",
        ),
    )
    async def _add(self, ctx, name: CMDName, *, content: str):
        perm = await self.ccModeCheck(ctx, "add")
        if not perm:
            raise CCommandNoPerm

        # Check if command already exists
        await self.isCmdExist(ctx, name)

        # Adding command to database
        lastInsert, lastLastInsert = await self.addCmd(ctx, name, content)
        if lastInsert and lastLastInsert:
            await ctx.send("`{}` has been created".format(name))

    @command.command(
        aliases=["/"],
        brief="Add an alias to a custom command",
        example=(
            "command alias example-cmd test-cmd",
            "command alias leaderboard board",
        ),
    )
    async def alias(self, ctx, command: CMDName, alias: CMDName):
        command = await getCustomCommand(ctx, command)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if alias == command.name:
            return await ctx.try_reply("Alias can't be identical to original name!")
        if alias in command.aliases:
            return await ctx.try_reply("Alias `{}` already exists!".format(alias))

        async with ctx.db.transaction():
            lastInsert = await ctx.db.execute(
                dbQuery.insertToCommandsLookup,
                values={
                    "cmdId": command.id,
                    "name": alias,
                    "guildId": ctx.guild.id,
                },
            )
            if lastInsert:
                return await ctx.try_reply(
                    "Alias `{}` for `{}` has been created".format(alias, command)
                )

    @command.group(
        name="edit",
        aliases=["&", "set"],
        brief="Edit custom command's property",
        description=(
            "Edit custom command's property\n\nBy default, will edit command's "
            "content when there is no subcommand specified"
        ),
        example=(
            "cmd set category example-cmd info",
            "cmd edit cat test-embed unsorted",
            "command & mode 0",
            "command & example-cmd This is an edit",
        ),
        invoke_without_command=True,
    )
    async def cmdSet(self, ctx, name: CMDName, *, content):
        await self.setContent(ctx, name, content=content)

    @cmdSet.command(
        name="content",
        aliases=["cont"],
        brief="Edit custom command's content",
    )
    async def setContent(self, ctx, name: CMDName, *, content):
        command = await getCustomCommand(ctx, name)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        update = await self.updateCommandContent(ctx, command, content)
        if update:
            return await ctx.try_reply("Command `{}` has been edited\n".format(name))

    @cmdSet.command(
        name="url",
        aliases=["u"],
        brief="Alias for `command update-url`",
    )
    async def setUrl(self, ctx, name: CMDName, url: str):
        await self.update_url(ctx, name, url)

    @cmdSet.command(
        name="alias",
        brief="Alias for `command alias`",
    )
    async def setAlias(self, ctx, command: CMDName, alias: CMDName):
        await self.alias(ctx, command, alias)

    @cmdSet.command(
        aliases=["cat", "mv"],
        brief="Move a custom command to a category",
    )
    async def category(self, ctx, command: CMDName, category: CMDName):
        category = category.lower()

        availableCats = [
            cog.qualified_name.lower()
            for cog in ctx.bot.cogs.values()
            if getattr(cog, "cc", False)
        ]
        if category not in availableCats:
            return await ctx.try_reply("Invalid category")

        command = await getCustomCommand(ctx, command)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if command.category == category:
            return await ctx.try_reply("{} already in {}!".format(command, category))
        # TODO: Add the actual stuff

    @cmdSet.command(
        name="mode",
        brief="Set custom command 'mode'",
        description=(
            "Set custom command 'mode'\n\n__**Modes:**__\n> `0`: Mods-only\n> "
            "`1`: Member can add command but only able to manage their own "
            "command\n> `2`: Member can add AND manage custom command (Anarchy "
            "mode)"
        ),
        example=(
            "command set mode 0",
            "cmd set mode 1",
            "cmd set mode 2",
        ),
    )
    @checks.is_mod()
    async def setMode(self, ctx, mode: int):
        if mode > 2:
            return await ctx.try_reply("There's only 3 (0, 1, 2) mode!")

        result = await self.bot.setGuildConfig(ctx.guild.id, "ccMode", mode)
        if result is not None:
            return await ctx.try_reply(
                "Custom command mode has been set to `{}`".format(mode)
            )

    @command.command(
        aliases=["-", "rm"],
        brief="Remove a custom command",
    )
    async def remove(self, ctx, name: CMDName):
        command = await getCustomCommand(ctx, name)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

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
            #   also `foreign_keys` enabled if you're using sqlite3
            async with ctx.db.transaction():
                await ctx.db.execute(dbQuery.deleteCommand, values={"id": command.id})
        # TODO: Adjust removed message
        return await ctx.try_reply(
            "{}`{}` has been removed".format("Alias " if isAlias else "", name)
        )

    @command.command(
        brief="Disable a command",
        description=(
            "Disable a command.\n\nSupport both custom and built-in "
            "command.\n(Will try to disable custom command or built-in if "
            "you're a moderator by default)\nNote: "
            "Server admin/mods still able to use disabled **built-in** "
            "command.\n\n__**Options:**__\n`--built-in` | `-b`: Disable "
            "built-in command\n`--custom` | `-c`: Disable custom command "
            "(Always overrides `--built-in`)\n`--category` | `-C`: Disable all "
            "commands in a specific category (Requires `-b`)"
        ),
        example=(
            "command disable example",
            "cmd disable -b weather",
            "command disable -bC info",
            "cmd disable -c test",
        ),
    )
    async def disable(self, ctx, *, arguments):
        # parse name and flags from arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--built-in", "-b", action="store_true")
        parser.add_argument("--custom", "-c", action="store_true")
        parser.add_argument("--category", "-C", action="store_true")
        parser.add_argument("name", nargs="+")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        isMod = await checks.isMod(ctx)

        # default mode
        mode = "built-in" if isMod else "custom"

        if parsed.built_in and not parsed.custom:
            mode = "built-in" if not parsed.category else "category"
        if not parsed.built_in and parsed.custom:
            mode = "custom"

        name = " ".join(parsed.name)

        successMsg = "`{}` has been disabled"
        alreadyMsg = "`{}` already disabled!"
        notFoundMsg = "There is not {} command called `{}`"
        immuneRoot = ("help", "command")

        if mode in ("built-in", "category"):
            # check if executor is a mod for built-in and category mode
            if not isMod:
                return await ctx.try_reply(
                    "Only mods allowed to disable built-in command"
                )

        if mode == "built-in":
            command = self.bot.get_command(name)
            if not command:
                # check if command exists
                return await ctx.try_reply(notFoundMsg.format(mode, name))

            # format command name
            cmdName = self.formatCmdName(command)

            if str(command.root_parent or cmdName) in immuneRoot:
                # check if command root parent is immune
                return await ctx.try_reply("This command can't be disabled!")

            # Make sure disable command is cached from database
            await self.getDisabledCommands(ctx, ctx.guild.id)

            try:
                self.bot.cache.disabled.append(ctx.guild.id, cmdName)
            except CacheUniqueViolation:
                # check if command already disabled
                return await ctx.try_reply(alreadyMsg.format(cmdName))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                    INSERT INTO disabled VALUES (:guildId, :command)
                    """,
                    values={"guildId": ctx.guild.id, "command": cmdName},
                )

                return await ctx.try_reply(successMsg.format(cmdName))

        elif mode == "category":
            category = self.bot.get_cog(name)
            commands = [
                c.name for c in category.get_commands() if c.name not in immuneRoot
            ]

            # Make sure disable command is cached from database
            await self.getDisabledCommands(ctx, ctx.guild.id)

            added = []
            for c in commands:
                try:
                    self.bot.cache.disabled.append(ctx.guild.id, c)
                    added.append(c)
                except CacheUniqueViolation:
                    continue

            if not added:
                return await ctx.try_reply("No commands succesfully disabled")

            async with ctx.db.transaction():
                await ctx.db.execute_many(
                    """
                    INSERT INTO disabled VALUES (:guildId, :command)
                    """,
                    values=[{"guildId": ctx.guild.id, "command": cmd} for cmd in added],
                )

                return await ctx.try_reply(
                    "`{}` commands has been disabled".format(len(added))
                )

        elif mode == "custom":
            try:
                command = await getCustomCommand(ctx, name)
            except CCommandNotFound:
                return await ctx.try_reply(notFoundMsg.format(mode, name))

            perm = await self.ccModeCheck(ctx, command=command)
            if not perm:
                raise CCommandNoPerm

            if not command.enabled:
                return await ctx.try_reply(alreadyMsg.format(name))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                        UPDATE commands
                        SET enabled=0
                        WHERE id=:id
                    """,
                    values={"id": command.id},
                )
                return await ctx.try_reply(successMsg.format(name))

    @command.command(
        brief="Enable a command",
        description=(
            "Enable a command.\n\nSupport both custom and built-in "
            "command.\n(Will try to enable custom command or built-in if "
            "you're a moderator by default)\nNote: "
            "__**Options:**__\n`--built-in` | `-b`: Enable built-in "
            "command\n`--custom` | `-c`: Enable custom command "
            "(Always overrides `--built-in`)\n`--category` | `-C`: Enable all "
            "commands in a specific category (Requires `-b`)"
        ),
        example=(
            "command enable example",
            "cmd enable -b weather",
            "cmd enable -bC info",
            "cmd enable -c test",
        ),
    )
    async def enable(self, ctx, *, arguments):
        # parse name and flags from arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--built-in", "-b", action="store_true")
        parser.add_argument("--custom", "-c", action="store_true")
        parser.add_argument("--category", "-C", action="store_true")
        parser.add_argument("name", nargs="+")

        parsed, _ = parser.parse_known_args(shlex.split(arguments))

        isMod = await checks.isMod(ctx)

        # default mode
        mode = "built-in" if isMod else "custom"

        if parsed.built_in and not parsed.custom:
            mode = "built-in" if not parsed.category else "category"
        if not parsed.built_in and parsed.custom:
            mode = "custom"

        name = " ".join(parsed.name)

        successMsg = "`{}` has been enabled"
        alreadyMsg = "`{}` already enabled!"
        notFoundMsg = "There is not {} command called `{}`"

        if mode in ("built-in", "category"):
            # check if executor is a mod for built-in and category mode
            if not isMod:
                return await ctx.try_reply(
                    "Only mods allowed to enable built-in command"
                )

        if mode == "built-in":
            command = self.bot.get_command(name)
            if not command:
                # check if command exists
                return await ctx.try_reply(notFoundMsg.format(mode, name))

            # format command name
            cmdName = self.formatCmdName(command)

            await self.getDisabledCommands(ctx, ctx.guild.id)

            try:
                self.bot.cache.disabled.remove(ctx.guild.id, cmdName)
            except ValueError:
                # check if command already enabled
                return await ctx.try_reply(alreadyMsg.format(cmdName))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                    DELETE FROM disabled
                    WHERE
                        guildId=:guildId AND command=:command
                    """,
                    values={"guildId": ctx.guild.id, "command": cmdName},
                )

                return await ctx.try_reply(successMsg.format(cmdName))

        elif mode == "category":
            category = self.bot.get_cog(name)
            await self.getDisabledCommands(ctx, ctx.guild.id)
            commands = [c.name for c in category.get_commands()]

            removed = []
            for c in commands:
                try:
                    self.bot.cache.disabled.remove(c)
                    removed.append(c)
                except ValueError:
                    continue

            if not removed:
                return await ctx.try_reply("No commands succesfully enabled")

            async with ctx.db.transaction():
                await ctx.db.execute_many(
                    """
                    DELETE FROM disabled WHERE guildId=:guildId AND command=:command
                    """,
                    values=[
                        {"guildId": ctx.guild.id, "command": cmd} for cmd in removed
                    ],
                )

                return await ctx.try_reply(
                    "`{}` commands has been enabled".format(len(removed))
                )

        elif mode == "custom":
            try:
                command = await getCustomCommand(ctx, name)
            except CCommandNotFound:
                return await ctx.try_reply(notFoundMsg.format(mode, name))

            perm = await self.ccModeCheck(ctx, command=command)
            if not perm:
                raise CCommandNoPerm

            if command.enabled:
                return await ctx.try_reply(alreadyMsg.format(name))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                        UPDATE commands
                        SET enabled=1
                        WHERE id=:id
                    """,
                    values={"id": command.id},
                )
                return await ctx.try_reply(successMsg.format(name))

    @command.command(
        aliases=["?"],
        brief="Show command's information",
        description=(
            "Show command's information.\n\nSimilar to `help` but "
            "prioritize custom commands"
        ),
        example=("command info help", "cmd info command", "cmd ? example-cmd"),
    )
    async def info(self, ctx, *, name):
        # Executes {prefix}help {name} if its built-in command
        try:
            command = await getCustomCommand(ctx, name)
            e = await formatCommandInfo(ctx.clean_prefix, command)
            return await ctx.try_reply(embed=e)
        except CCommandNotFound:
            return await ctx.send_help(name)

    @commands.command(brief="Get link to my source code")
    async def source(self, ctx):
        await ctx.send("My source code: {}".format(self.bot.links["Source Code"]))

    @commands.command(aliases=["botinfo", "bi"], brief="Information about me")
    async def about(self, ctx):
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

    @commands.command(brief="Information about my stats")
    async def stats(self, ctx):
        uptime = utcnow() - self.bot.uptime
        e = ZEmbed.default(ctx)
        e.set_author(
            name=ctx.bot.user.name + "'s stats", icon_url=ctx.bot.user.avatar_url
        )
        e.add_field(
            name="🕙 | Uptime", value=humanize.precisedelta(uptime), inline=False
        )
        e.add_field(
            name="<:terminal:852787866554859591> | Command Usage (This session)",
            value="{} commands ({} custom commands)".format(
                self.bot.commandUsage, self.bot.customCommandUsage
            ),
            inline=False,
        )
        await ctx.try_reply(embed=e)

    @commands.group(
        aliases=["pref"],
        brief="Manages bot's custom prefix",
        example=(
            "prefix add ?",
            "pref remove !",
        ),
        invoke_without_command=True,
    )
    async def prefix(self, ctx):
        await ctx.try_invoke(self.prefList)

    @prefix.command(
        name="list",
        aliases=["ls"],
        brief="Get all prefixes",
        exemple=("prefix ls", "pref list"),
    )
    async def prefList(self, ctx):
        prefixes = await self.bot.getGuildPrefix(ctx.guild.id)
        menu = ZMenu(source=PrefixesPageSource(ctx, ["placeholder"] * 2 + prefixes))
        await menu.start(ctx)

    @prefix.command(
        name="add",
        aliases=["+"],
        brief="Add a custom prefix",
        description=(
            'Add a custom prefix.\n\n Tips: Use quotation mark (`""`) to add '
            "spaces to your prefix."
        ),
        example=("prefix add ?", 'prefix + "please do "', "pref + z!"),
    )
    @checks.is_mod()
    async def prefAdd(self, ctx, *prefix):
        prefix = " ".join(prefix).lstrip()
        if not prefix:
            return await ctx.error("Prefix can't be empty!")

        try:
            await self.bot.addPrefix(ctx.guild.id, prefix)
            await ctx.try_reply(
                "Prefix `{}` has been added".format(cleanifyPrefix(self.bot, prefix))
            )
        except Exception as exc:
            await ctx.error(exc)

    @prefix.command(
        name="remove",
        aliases=["-", "rm"],
        brief="Remove a custom prefix",
        example=("prefix rm ?", 'prefix - "please do "', "pref remove z!"),
    )
    @checks.is_mod()
    async def prefRm(self, ctx, *prefix):
        prefix = " ".join(prefix).lstrip()
        if not prefix:
            return await ctx.error("Prefix can't be empty!")

        try:
            await self.bot.rmPrefix(ctx.guild.id, prefix)
            await ctx.try_reply(
                "Prefix `{}` has been removed".format(cleanifyPrefix(self.bot, prefix))
            )
        except Exception as exc:
            await ctx.error(exc)

    @commands.command(aliases=["p"], brief="Get bot's response time")
    async def ping(self, ctx):
        start = time.perf_counter()
        e = ZEmbed.default(ctx, title="Pong!")
        e.add_field(
            name="<a:discordLoading:857138980192911381> | Websocket",
            value=f"{round(self.bot.latency*1000)}ms",
        )
        msg = await ctx.try_reply(embed=e)
        end = time.perf_counter()
        msg_ping = (end - start) * 1000
        e.add_field(
            name="<a:typing:785053882664878100> | Typing",
            value=f"{round(msg_ping)}ms",
            inline=False,
        )
        await msg.edit(embed=e)


def setup(bot):
    bot.add_cog(Meta(bot))
