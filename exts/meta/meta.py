"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import annotations

import difflib
import re
import time
from typing import TYPE_CHECKING

import discord
import humanize
import TagScriptEngine as tse
from discord.ext import commands

from core import checks
from core.embed import ZEmbed
from core.errors import (
    CCommandAlreadyExists,
    CCommandDisabled,
    CCommandNoPerm,
    CCommandNotFound,
    CCommandNotInGuild,
)
from core.menus import ZMenuPagesView
from core.mixin import CogMixin
from utils import dbQuery, sql, tseBlocks
from utils.cache import CacheListProperty, CacheUniqueViolation
from utils.format import CMDName, cleanifyPrefix
from utils.other import ArgumentParser, reactsToMessage, utcnow

from ._custom_command import getCustomCommand, getCustomCommands
from ._help import CustomHelp
from ._objects import CustomCommand
from ._pages import PrefixesPageSource


if TYPE_CHECKING:
    from core.bot import ziBot


GIST_REGEX = re.compile(
    r"http(?:s)?:\/\/gist\.github(?:usercontent)?\.com\/.*\/(\S*)(?:\/)?"
)
PASTEBIN_REGEX = re.compile(r"http(?:s)?:\/\/pastebin.com\/(?:raw\/)?(\S*)")


DIFFER = difflib.Differ()


# CC Modes
MODES = [
    "Only mods can add and manage custom commands",
    "Member can add custom command but can only manage **their own** commands",
    "**A N A R C H Y**",
]


class Meta(commands.Cog, CogMixin):
    """Bot-related commands."""

    icon = "🤖"
    cc = True

    def __init__(self, bot: ziBot):
        super().__init__(bot)

        # Custom help command stuff
        # help command's attribute
        attributes = dict(
            name="help",
            aliases=("?",),
            usage="[category / command]",
            brief="Get information of a command or category",
            description=(
                "Get information of a command or category.\n\n"
                "You can use `filters` flag to set priority.\n"
                "For example: `>help command filters: custom built-in`, will try to "
                "get custom command called `command` first before getting built-in "
                "command with the same name, **BUT** will not try to get category "
                "named `command`.\n\n"
                "All available filters: `category` (`cat`, `C`), `custom` (`c`), and "
                "`built-in` (`b`)"
            ),
            extras=dict(
                example=(
                    "help info",
                    "? weather",
                    "help custom-cmd filters: custom",
                ),
                flags={
                    ("filters", "filter", "filt"): (
                        "Filter command type or category, "
                        "also work as priority system."
                    ),
                },
            ),
        )
        # Backup the old/original command incase this cog unloaded
        self._original_help_command = bot.help_command
        # Replace default help menu with custom one
        self.bot.help_command = CustomHelp(command_attrs=attributes)
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
        if not ctx.guild:
            return True
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
            kwargs = {"reference": ctx.replied_reference}
            if dest:
                if dest == "reply":
                    action = ctx.try_reply
                    kwargs["reference"] = ctx.replied_reference or ctx.message
                if dest == "dm":
                    action = ctx.author.send
                    kwargs = {}

            msg = await action(
                result.body or ("\u200b" if not embed else ""),
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False
                ),
                **kwargs,
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
        mode = await self.bot.getGuildConfig(ctx.guild.id, "ccMode") or 0

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
    @commands.group(
        aliases=("cmd", "tag", "script"),
        brief="Manage commands",
        description=(
            "Manage commands\n\n**NOTE**: Custom Commands only available for "
            "guilds/servers!"
        ),
    )
    @commands.guild_only()
    async def command(self, ctx):
        pass

    @command.command(aliases=("exec", "execute"), brief="Execute a custom command")
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
        # TODO: Drop pastebin support replace it with hastebin
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
        aliases=("++",),
        brief="Import a custom command from pastebin/gist.github",
        extras=dict(
            example=(
                "command import pastebin-cmd https://pastebin.com/ZxvGqEAs",
                "command ++ gist "
                "https://gist.github.com/null2264/87c89d2b5e2453529e29c2cae3b57729",
            ),
            perms={
                "user": "Depends on custom command mode",
            },
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
            await ctx.success(
                "**Source**: <{}>".format(url),
                title="`{}` has been imported".format(name),
            )

    @command.command(
        name="update-url",
        aliases=("&u", "set-url"),
        brief="Update imported command's source url",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def update_url(self, ctx, name: CMDName, url: str):
        # NOTE: Can only be run by cmd owner or guild mods/owner
        command = await getCustomCommand(ctx, name)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if not command.url:
            # Incase someone try to update `text` command
            return await ctx.error(
                "Please use `{}command edit` instead!".format(ctx.clean_prefix),
                title="`{}` is not imported command!".format(name),
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
            return await ctx.success(
                "\nYou can do `{}command update {}` to update the content".format(
                    ctx.clean_prefix, name
                ),
                title="`{}` url has been set to <{}>".format(name, url),
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
        aliases=("&&", "pull"),
        brief="Update imported command's content",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
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
            return await ctx.error(
                "Please use `{}command edit` instead!".format(ctx.clean_prefix),
                title="`{}` is not imported command!".format(name),
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
            return await ctx.success(
                "\n[**Note**]: It takes awhile for the site to be updated!",
                title="Already up to date.",
            )

        update = await self.updateCommandContent(ctx, command, content)
        if update:
            return await ctx.success(
                (
                    "`[+]` {} Additions\n".format(addition)
                    + "`[-]` {} Deletions".format(deletion)
                ),
                title="Command `{}` has been update\n".format(name),
            )

    @command.command(
        name="add",
        aliases=("+", "create"),
        brief="Create a new custom command",
        extras=dict(
            example=(
                "command add example-cmd Just an example",
                "cmd + hello Hello World!",
            ),
            perms={
                "user": "Depends on custom command mode",
            },
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
            await ctx.success(title="Command `{}` has been created".format(name))

    @command.command(
        aliases=("/",),
        brief="Add an alias to a custom command",
        usage="(command name) (alias)",
        extras=dict(
            example=(
                "command alias example-cmd test-cmd",
                "command alias leaderboard board",
            ),
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def alias(self, ctx, commandName: CMDName, alias: CMDName):
        command: CustomCommand = await getCustomCommand(ctx, commandName)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if alias == command.name:
            return await ctx.error("Alias can't be identical to original name!")
        if alias in command.aliases:
            return await ctx.error("Alias `{}` already exists!".format(alias))

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
                return await ctx.success(
                    title="Alias `{}` for `{}` has been created".format(alias, command)
                )

    @command.command(
        name="edit",
        brief="Edit custom command's content",
        description=(
            "Edit custom command's content.\n\n" "Alias for `command set content`"
        ),
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def cmdEdit(self, ctx, command: CMDName, *, content):
        await self.setContent(ctx, command, content=content)

    @command.group(
        name="set",
        brief="Edit custom command's property",
        description=(
            "Edit custom command's property\n\nBy default, will edit command's "
            "content when there is no subcommand specified"
        ),
        extras=dict(
            example=(
                "cmd set category example-cmd info",
                "cmd edit cat test-embed unsorted",
                "command & mode 0",
                "command & example-cmd This is an edit",
            )
        ),
    )
    async def cmdSet(self, ctx):
        pass

    @cmdSet.command(
        name="content",
        aliases=("cont",),
        brief="Edit custom command's content",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def setContent(self, ctx, name: CMDName, *, content):
        command = await getCustomCommand(ctx, name)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        update = await self.updateCommandContent(ctx, command, content)
        if update:
            return await ctx.success(
                title="Command `{}` has been edited\n".format(name)
            )

    @cmdSet.command(
        name="url",
        aliases=("u",),
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
        name="category",
        aliases=("cat", "mv"),
        usage="(command) (category)",
        brief="Move a custom command to a category",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
    )
    async def setCategory(self, ctx, _command: CMDName, category: CMDName):
        category = category.lower()

        availableCats = [
            cog.qualified_name.lower()
            for cog in ctx.bot.cogs.values()
            if getattr(cog, "cc", False)
        ]
        if category not in availableCats:
            return await ctx.error(title="Invalid category")

        command = await getCustomCommand(ctx, _command)

        perm = await self.ccModeCheck(ctx, command=command)
        if not perm:
            raise CCommandNoPerm

        if command.category == category:
            return await ctx.success(
                title="{} already in {}!".format(command, category)
            )

        async with ctx.db.transaction():
            query = sql.commands.update(sql.commands.c.id == command.id).values(
                category=category
            )
            await ctx.db.execute(query)
            return await ctx.success(
                title="{}'s category has been set to {}!".format(command, category)
            )

    @cmdSet.command(
        name="mode",
        brief="Set custom command 'mode'",
        description=(
            "Set custom command 'mode'\n\n__**Modes:**__\n> `0`: Mods-only\n> "
            "`1`: Member can add command but only able to manage their own "
            "command\n> `2`: Member can add AND manage custom command (Anarchy "
            "mode)"
        ),
        extras=dict(
            example=(
                "command set mode 0",
                "cmd set mode 1",
                "cmd set mode 2",
            ),
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guilds",
            },
        ),
    )
    @checks.is_mod()
    async def setMode(self, ctx, mode: int):
        if mode > 2:
            return await ctx.error(title="There's only 3 available mode! (0, 1, 2)")

        result = await self.bot.setGuildConfig(ctx.guild.id, "ccMode", mode)
        if result is not None:
            return await ctx.success(
                MODES[mode],
                title="Custom command mode has been set to `{}`".format(mode),
            )

    @command.command(
        aliases=("-", "rm"),
        brief="Remove a custom command",
        extras=dict(
            perms={
                "user": "Depends on custom command mode",
            },
        ),
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
        return await ctx.success(
            title="{} `{}` has been removed".format(
                "Alias" if isAlias else "Command", name
            )
        )

    @command.command(
        brief="Disable a command",
        description=(
            "Disable a command.\n\n"
            "Support both custom and built-in command.\n"
            "(Will try to disable custom command or built-in if "
            "you're a moderator by default)\n"
            "Note: Server admin/mods still able to use disabled **built-in** "
            "command."
        ),
        extras=dict(
            example=(
                "command disable example",
                "cmd disable built-in: on weather",
                "command disable built-in: on cat: on info",
                "cmd disable custom: on test",
            ),
            flags={
                "built-in": "Disable built-in command",
                "custom": "Disable custom command",
                (
                    "category",
                    "cat",
                ): "Disable all command in a specific category (Requires `built-in` flag)",
            },
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guild (Built-in only)",
            },
        ),
        usage="(name) [options]",
    )
    async def disable(self, ctx, *, arguments):
        # parse name and flags from arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--built-in", action="bool")
        parser.add_argument("--custom", action="bool")
        parser.add_argument("--category", aliases=("--cat",), action="bool")
        parser.add_argument("name", action="extend", nargs="+")
        parser.add_argument("--name", action="extend", nargs="+")

        # parsed, _ = parser.parse_known_args(shlex.split(arguments))
        parsed, _ = await parser.parse_known_from_string(arguments)

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
                return await ctx.error(
                    title="Only mods allowed to disable built-in command"
                )

        if mode == "built-in":
            command = self.bot.get_command(name)
            if not command:
                # check if command exists
                return await ctx.error(title=notFoundMsg.format(mode, name))

            # format command name
            cmdName = self.formatCmdName(command)

            if str(command.root_parent or cmdName) in immuneRoot:
                # check if command root parent is immune
                return await ctx.error(title="This command can't be disabled!")

            # Make sure disable command is cached from database
            await self.getDisabledCommands(ctx, ctx.guild.id)

            try:
                self.bot.cache.disabled.append(ctx.guild.id, cmdName)
            except CacheUniqueViolation:
                # check if command already disabled
                return await ctx.error(title=alreadyMsg.format(cmdName))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                    INSERT INTO disabled VALUES (:guildId, :command)
                    """,
                    values={"guildId": ctx.guild.id, "command": cmdName},
                )

                return await ctx.success(title=successMsg.format(cmdName))

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
                return await ctx.error(title="No commands succesfully disabled")

            async with ctx.db.transaction():
                await ctx.db.execute_many(
                    """
                    INSERT INTO disabled VALUES (:guildId, :command)
                    """,
                    values=[{"guildId": ctx.guild.id, "command": cmd} for cmd in added],
                )

                return await ctx.success(
                    title="`{}` commands has been disabled".format(len(added))
                )

        elif mode == "custom":
            try:
                command = await getCustomCommand(ctx, name)
            except CCommandNotFound:
                return await ctx.error(title=notFoundMsg.format(mode, name))

            perm = await self.ccModeCheck(ctx, command=command)
            if not perm:
                raise CCommandNoPerm

            if not command.enabled:
                return await ctx.error(title=alreadyMsg.format(name))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                        UPDATE commands
                        SET enabled=0
                        WHERE id=:id
                    """,
                    values={"id": command.id},
                )
                return await ctx.success(title=successMsg.format(name))

    @command.command(
        brief="Enable a command",
        description=(
            "Enable a command.\n\n"
            "Support both custom and built-in command.\n"
            "(Will try to enable custom command or built-in if "
            "you're a moderator by default)"
        ),
        extras=dict(
            example=(
                "command enable example",
                "cmd enable built-in: on weather",
                "cmd enable built-in: on cat: on info",
                "cmd enable custom: on test",
            ),
            flags={
                "built-in": "Emable built-in command",
                "custom": "Enable custom command",
                (
                    "category",
                    "cat",
                ): "Enable all command in a specific category (Requires `built-in` flag)",
            },
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guild (Built-in only)",
            },
        ),
        usage="(name) [options]",
    )
    async def enable(self, ctx, *, arguments):
        # parse name and flags from arguments
        parser = ArgumentParser(allow_abbrev=False)
        parser.add_argument("--built-in", action="bool")
        parser.add_argument("--custom", action="bool")
        parser.add_argument("--category", aliases=("--cat",), action="bool")
        parser.add_argument("name", action="extend", nargs="+")
        parser.add_argument("--name", action="extend", nargs="+")

        parsed, _ = await parser.parse_known_from_string(arguments)

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
                return await ctx.error(
                    title="Only mods allowed to enable built-in command"
                )

        if mode == "built-in":
            command = self.bot.get_command(name)
            if not command:
                # check if command exists
                return await ctx.error(title=notFoundMsg.format(mode, name))

            # format command name
            cmdName = self.formatCmdName(command)

            await self.getDisabledCommands(ctx, ctx.guild.id)

            try:
                self.bot.cache.disabled.remove(ctx.guild.id, cmdName)
            except ValueError:
                # check if command already enabled
                return await ctx.error(title=alreadyMsg.format(cmdName))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                    DELETE FROM disabled
                    WHERE
                        guildId=:guildId AND command=:command
                    """,
                    values={"guildId": ctx.guild.id, "command": cmdName},
                )

                return await ctx.success(title=successMsg.format(cmdName))

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
                return await ctx.error(title="No commands succesfully enabled")

            async with ctx.db.transaction():
                await ctx.db.execute_many(
                    """
                    DELETE FROM disabled WHERE guildId=:guildId AND command=:command
                    """,
                    values=[
                        {"guildId": ctx.guild.id, "command": cmd} for cmd in removed
                    ],
                )

                return await ctx.success(
                    title="`{}` commands has been enabled".format(len(removed))
                )

        elif mode == "custom":
            try:
                command = await getCustomCommand(ctx, name)
            except CCommandNotFound:
                return await ctx.error(title=notFoundMsg.format(mode, name))

            perm = await self.ccModeCheck(ctx, command=command)
            if not perm:
                raise CCommandNoPerm

            if command.enabled:
                return await ctx.error(title=alreadyMsg.format(name))

            async with ctx.db.transaction():
                await ctx.db.execute(
                    """
                        UPDATE commands
                        SET enabled=1
                        WHERE id=:id
                    """,
                    values={"id": command.id},
                )
                return await ctx.success(title=successMsg.format(name))

    @command.command(
        aliases=("?",),
        brief="Show command's information",
        description=("Show command's information.\n\nAlias for `help`"),
        extras=dict(
            example=(
                "command info help",
                "cmd info command",
                "cmd ? example-cmd",
                "cmd ? cmd filters: custom built-in",
            )
        ),
    )
    async def info(self, ctx, *, name: str = None):
        cmd: CustomHelp = ctx.bot.help_command
        cmd = cmd.copy()
        cmd.context = ctx
        await cmd.command_callback(ctx, command=name)

    @command.command(name="list", aliases=("ls",), brief="Show all custom commands")
    async def cmdList(self, ctx):
        # TODO: Merge this command with help command
        cmds = await getCustomCommands(ctx.db, ctx.guild.id)
        cmds = sorted(cmds, key=lambda cmd: cmd.uses, reverse=True)
        e = ZEmbed.default(ctx, title="Custom Commands", description="")
        if cmds:
            for k, v in enumerate(cmds):
                e.description += "**`{}`** {} [`{}` uses]\n".format(
                    k + 1, v.name, v.uses
                )
        else:
            e.description = "This server doesn't have custom command"
        await ctx.try_reply(embed=e)

    @command.command(name="mode", brief="Show current custom command mode")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cmdMode(self, ctx):
        mode = await self.bot.getGuildConfig(ctx.guild.id, "ccMode") or 0

        e = ZEmbed.minimal(
            title="Current Mode: `{}`".format(mode), description=MODES[mode]
        )
        return await ctx.try_reply(embed=e)

    @command.command(name="modes", brief="Show all different custom command modes")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cmdModes(self, ctx):
        e = ZEmbed.minimal(
            title="Custom Command Modes",
            fields=[("Mode `{}`".format(k), v) for k, v in enumerate(MODES)],
        )
        e.set_footer(
            text="Use `{}command set mode [mode]` to set the mode!".format(
                ctx.clean_prefix
            )
        )
        return await ctx.try_reply(embed=e)

    @commands.command(
        name="commands",
        aliases=("cmds",),
        brief="Show all custom commands. Alias for `command list`",
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def _commands(self, ctx):
        await ctx.try_invoke(self.cmdList)

    @commands.command(brief="Get link to my source code")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def source(self, ctx):
        await ctx.send("My source code: {}".format(self.bot.links["Source Code"]))

    @commands.command(aliases=("botinfo", "bi"), brief="Information about me")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def about(self, ctx):
        # Z3R0 Banner
        f = discord.File("./assets/img/banner.png", filename="banner.png")

        e = ZEmbed.default(
            ctx,
            description=self.bot.description
            + "\n\nThis bot is licensed under **{}**.".format(ctx.bot.license),
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar.url)
        e.set_image(url="attachment://banner.png")
        e.add_field(name="Author", value=ctx.bot.author)
        e.add_field(
            name="Library",
            value="[`zidiscord.py`](https://github.com/null2264/discord.py) - `v{}`".format(
                discord.__version__
            ),
        )
        e.add_field(name="Version", value=ctx.bot.version)
        view = discord.ui.View()
        for k, v in ctx.bot.links.items():
            if k and v:
                view.add_item(discord.ui.Button(label=k, url=v))
        await ctx.try_reply(file=f, embed=e, view=view)

    @commands.command(brief="Information about my stats")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx):
        uptime = utcnow() - self.bot.uptime
        e = ZEmbed.default(ctx)
        e.set_author(
            name=ctx.bot.user.name + "'s stats", icon_url=ctx.bot.user.avatar.url
        )
        e.add_field(
            name="🕙 | Uptime", value=humanize.precisedelta(uptime), inline=False
        )
        e.add_field(
            name="<:terminal:852787866554859591> | Command Usage (This session)",
            value="{} commands ({} custom commands)".format(
                sum(self.bot.commandUsage.values()), self.bot.customCommandUsage
            ),
            inline=False,
        )
        await ctx.try_reply(embed=e)

    @commands.group(
        aliases=("pref",),
        brief="Manages bot's custom prefix",
        extras=dict(
            example=(
                "prefix add ?",
                "pref remove !",
            )
        ),
        invoke_without_command=True,
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix(self, ctx):
        await ctx.try_invoke(self.prefList)

    @prefix.command(
        name="list",
        aliases=("ls",),
        brief="Get all prefixes",
        exemple=("prefix ls", "pref list"),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefList(self, ctx):
        prefixes = await self.bot.getGuildPrefix(ctx.guild.id)
        menu = ZMenuPagesView(
            ctx, source=PrefixesPageSource(ctx, ["placeholder"] * 2 + prefixes)
        )
        await menu.start()

    @prefix.command(
        name="add",
        aliases=("+",),
        brief="Add a custom prefix",
        description=(
            'Add a custom prefix.\n\n Tips: Use quotation mark (`""`) to add '
            "spaces to your prefix."
        ),
        extras=dict(
            example=("prefix add ?", 'prefix + "please do "', "pref + z!"),
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guild",
            },
        ),
    )
    @checks.is_mod()
    async def prefAdd(self, ctx, *prefix):
        prefix = " ".join(prefix).lstrip()
        if not prefix:
            return await ctx.error("Prefix can't be empty!")

        try:
            await self.bot.addPrefix(ctx.guild.id, prefix)
            await ctx.success(
                title="Prefix `{}` has been added".format(
                    cleanifyPrefix(self.bot, prefix)
                )
            )
        except Exception as exc:
            await ctx.error(exc)

    @prefix.command(
        name="remove",
        aliases=("-", "rm"),
        brief="Remove a custom prefix",
        extras=dict(
            example=("prefix rm ?", 'prefix - "please do "', "pref remove z!"),
            perms={
                "bot": None,
                "user": "Moderator Role or Manage Guild",
            },
        ),
    )
    @checks.is_mod()
    async def prefRm(self, ctx, *prefix):
        prefix = " ".join(prefix).lstrip()
        if not prefix:
            return await ctx.error("Prefix can't be empty!")

        try:
            await self.bot.rmPrefix(ctx.guild.id, prefix)
            await ctx.success(
                title="Prefix `{}` has been removed".format(
                    cleanifyPrefix(self.bot, prefix)
                )
            )
        except Exception as exc:
            await ctx.error(exc)

    @commands.command(aliases=("p",), brief="Get bot's response time")
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

    @commands.command(brief="Get bot's invite link")
    async def invite(self, ctx):
        clientId = self.bot.user.id
        e = ZEmbed(
            title=f"Want to invite {self.bot.user.name}?",
            description="[Invite with administrator permission]("
            + discord.utils.oauth_url(
                clientId,
                permissions=discord.Permissions(8),
            )
            + ")\n[Invite with necessary premissions (**recommended**)]("
            + discord.utils.oauth_url(
                clientId,
                permissions=discord.Permissions(4260883702),
            )
            + ")",
        )
        await ctx.try_reply(embed=e)
